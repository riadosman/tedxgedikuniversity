from django.utils.translation import gettext_lazy as tr
from django.core.exceptions import ValidationError, PermissionDenied
from django.db import transaction
from django.utils import timezone
from .permissions import require, roles, scoped, grants
from .services import audit, locked_event
from .models import ContentRevision
from .resources import RESOURCES


def validate_business(obj, actor):
    from operations.models import Task, TaskDependency, Incident
    from team.models import Shift
    from program.models import Talk, ScheduleItem, Rehearsal

    if isinstance(obj, Task):
        if obj.status == "completed" and obj.dependencies.exclude(depends_on__status="completed").exists():
            raise ValidationError(tr("Complete prerequisite tasks first."))
        if obj.status == "completed" and not (
            roles(actor, obj.event) & {"organizer", "event_admin"}
            or (
                obj.department_id is not None
                and grants(actor, obj.event).filter(role="leader", department_id=obj.department_id).exists()
            )
        ):
            obj.status = "needs_review"
    if isinstance(obj, TaskDependency):
        visited, pending = set(), [obj.depends_on_id]
        while pending:
            current = pending.pop()
            if current == obj.task_id:
                raise ValidationError(tr("This dependency would create a cycle."))
            if current not in visited:
                visited.add(current)
                pending.extend(
                    TaskDependency.objects.filter(event=obj.event, task_id=current).values_list(
                        "depends_on_id", flat=True
                    )
                )
    if isinstance(obj, Incident) and obj.status in {"resolved", "closed"} and not obj.resolution.strip():
        raise ValidationError(tr("Record the resolution before closing an incident."))
    if isinstance(obj, Talk) and obj.status == "approved":
        raise ValidationError(tr("Use the approval action to approve a reviewed talk."))
    if (
        isinstance(obj, Talk)
        and obj.status == "ready"
        and not all([obj.release_received, obj.fact_checked, obj.rights_cleared])
    ):
        raise ValidationError(
            tr("Complete the release, fact checking and rights review before marking this talk ready.")
        )
    if isinstance(obj, ScheduleItem):
        if obj.kind != "production" and not (
            obj.event.starts_at <= obj.starts_at < obj.ends_at <= obj.event.ends_at
        ):
            raise ValidationError(tr("Public sessions must fit inside the event's public hours."))
        if obj.kind == "talk":
            if not obj.talk_id:
                raise ValidationError(tr("Select the talk for this program item."))
            if (
                obj.event.max_talk_minutes
                and (obj.ends_at - obj.starts_at).total_seconds() > obj.event.max_talk_minutes * 60
            ):
                raise ValidationError(tr("This talk exceeds the configured event duration limit."))
        if (
            obj.kind != "production"
            and ScheduleItem.objects.filter(
                event=obj.event, starts_at__lt=obj.ends_at, ends_at__gt=obj.starts_at
            )
            .exclude(pk=obj.pk)
            .exclude(kind="production")
            .exists()
        ):
            raise ValidationError(tr("This session overlaps another public program item."))
    if (
        isinstance(obj, Rehearsal)
        and Rehearsal.objects.filter(
            event=obj.event,
            talk__speaker=obj.talk.speaker,
            starts_at__lt=obj.ends_at,
            ends_at__gt=obj.starts_at,
        )
        .exclude(pk=obj.pk)
        .exists()
    ):
        raise ValidationError(tr("The speaker already has a rehearsal at this time."))
    if isinstance(obj, Shift) and not obj._state.adding:
        from team.models import ShiftAssignment

        for assignment in ShiftAssignment.objects.filter(shift=obj).exclude(status="cancelled"):
            assignment.shift = obj
            assignment.clean()


@transaction.atomic
def save_resource(event, actor, key, form, expected_version=None):
    event = locked_event(event)
    obj = form.instance
    creating = obj._state.adding
    require(actor, event, key, "create" if creating else "edit")
    if not creating:
        current = scoped(type(obj).objects.select_for_update(), actor, event, key).get(pk=obj.pk)
        if (
            expected_version is None
            or not str(expected_version).isdigit()
            or current.version != int(expected_version)
        ):
            raise ValidationError(tr("This record changed while you were editing. Reload it before saving."))
        obj.version = current.version + 1
    obj.event = event
    if key == "attendees":
        from admissions.services import normalize_email, normalize_phone, normalize_plate
        from admissions.models import ActionToken
        from communications.models import Notification

        if creating:
            raise ValidationError(tr("Use the registration form to create an attendee and ticket together."))
        if obj.anonymized_at:
            raise ValidationError(tr("An anonymized attendee cannot be restored through correction."))
        if not form.cleaned_data.get("correction_reason", "").strip():
            raise ValidationError(tr("Record the reason for this correction."))
        obj.email = normalize_email(obj.email or "")
        # Older registrations have no phone; when given, it follows the registration form's rules.
        obj.phone = normalize_phone(obj.phone) if obj.phone else ""
        obj.vehicle_plate = normalize_plate(obj.vehicle_plate) if obj.arrives_by_car else ""
        if current.email != obj.email:
            ActionToken.objects.filter(attendee=obj).delete()
            Notification.objects.filter(
                event=event, recipient=current.email, status__in=["pending", "sending", "failed"]
            ).update(status="suppressed", payload_ciphertext="")
        audit(event, actor, "attendee.corrected", obj, reason=form.cleaned_data["correction_reason"])
    if key in {"departments", "shifts", "assignments", "dependencies", "runbook"} and not roles(
        actor, event
    ) & {"organizer", "event_admin"}:
        target = current if not creating else obj
        department_id = (
            target.pk
            if key == "departments"
            else target.shift.department_id
            if key == "assignments"
            else target.task.department_id
            if key == "dependencies"
            else target.department_id
        )
        if not grants(actor, event).filter(role="leader", department_id=department_id).exists():
            raise PermissionDenied(tr("Only the responsible department leader can change this record."))
    if key == "files":
        held = roles(actor, event)
        if "organizer" not in held:
            allowed = set()
            if "event_admin" in held:
                allowed |= {"leadership", "department", "task"}
            if "speaker_manager" in held:
                allowed.add("speaker")
            if "editor" in held:
                allowed.add("public_candidate")
            if "leader" in held:
                allowed |= {"department", "task"}
            if obj.scope not in allowed:
                raise PermissionDenied(tr("This file scope is not permitted for your role."))
        if (
            obj.scope == "department"
            and not obj.department_id
            or obj.scope == "task"
            and not obj.task_id
            or obj.scope == "speaker"
            and not obj.talk_id
        ):
            raise ValidationError(tr("Select the record that owns this private file."))
    if key == "roles" and not creating:
        from .models import RoleGrant

        if (
            current.role == "organizer"
            and current.active
            and (
                not obj.active
                or obj.role != "organizer"
                or obj.user_id != current.user_id
                or obj.expires_at is not None
            )
        ):
            if (
                not RoleGrant.objects.filter(
                    event=event, role="organizer", active=True, user__is_active=True, expires_at__isnull=True
                )
                .exclude(pk=obj.pk)
                .exists()
            ):
                raise ValidationError(tr("Keep at least one active organizer."))
    validate_business(obj, actor)
    if hasattr(obj, "approved_at"):
        obj.approved_at = None
    obj.save()
    audit(event, actor, f"{key}.{'created' if creating else 'updated'}", obj, fields=list(form.changed_data))
    return obj


@transaction.atomic
def action_resource(event, actor, key, pk, action, reason, *, ticket_type=None):
    event = locked_event(event)
    resource = RESOURCES[key]
    obj = scoped(resource.model.objects.select_for_update(), actor, event, key).filter(pk=pk).first()
    if obj is None:
        raise PermissionDenied(tr("This record is unavailable in your authorized scope."))
    if action not in resource.actions:
        raise PermissionDenied
    if key == "tickets":
        from admissions.services import cancel_ticket, rotate_ticket

        return (cancel_ticket if action == "cancel" else rotate_ticket)(event, actor, obj.pk, reason)
    if key == "privacy" and action == "anonymize":
        from .privacy import anonymize_attendee

        return anonymize_attendee(event, actor, obj.pk, reason)
    if key in {"attendees", "registrations"} and action == "delete":
        from .privacy import delete_registration

        return delete_registration(event, actor, obj.pk if key == "attendees" else obj.attendee_id, reason)
    if key == "notifications" and action == "retry":
        require(actor, event, key, "retry")
        if obj.status != "failed" or not reason.strip():
            raise ValidationError(tr("Only failed delivery jobs can be retried, with a recorded reason."))
        attempts = obj.attempts
        obj.status, obj.attempts, obj.next_attempt_at, obj.lease_until = "pending", 0, timezone.now(), None
        obj.save()
        audit(event, actor, "notification.retried", obj, previous_attempts=attempts, reason=reason[:250])
        return obj
    if key == "runbook" and action == "acknowledge":
        from operations.models import RunbookAcknowledgment

        if not obj.published_snapshot:
            raise ValidationError(tr("Only published runbook revisions can be acknowledged."))
        RunbookAcknowledgment.objects.get_or_create(
            event=event, item=obj, user=actor, revision=obj.published_snapshot["version"]
        )
        audit(event, actor, "runbook.acknowledged", obj, revision=obj.published_snapshot["version"])
        return obj
    if action == "publish" or (key == "talks" and action == "approve"):
        require(actor, event, key, "approve")
    elif action != "read":
        require(actor, event, key, "edit")
    if not reason.strip() and action != "read":
        raise ValidationError(tr("Add a reason or operational note."))
    if key == "pages":
        snapshot = {"title": obj.title, "body": obj.body, "language": obj.language, "version": obj.version}
        ContentRevision.objects.create(event=event, page=obj, snapshot=snapshot, approved_by=actor)
        obj.published_snapshot = snapshot
        obj.published_at = timezone.now()
    elif key == "applications":
        from team.models import Volunteer

        require(actor, event, key, "approve")
        if obj.status in {"accepted", "withdrawn"}:
            raise ValidationError(tr("This application is already finalized."))
        obj.status = action
        if action == "accepted":
            Volunteer.objects.get_or_create(
                event=event,
                application=obj,
                defaults={
                    "name": obj.name,
                    "email": obj.email,
                    "skills": obj.skills,
                    "languages": obj.languages,
                    "availability": obj.availability,
                },
            )
        from communications.services import enqueue

        enqueue(
            event,
            obj.email,
            "volunteer-decision",
            {"name": obj.name, "status": action, "link": ""},
            f"volunteer:{obj.pk}:{obj.version}:{action}",
        )
    elif key == "assignments":
        held = roles(actor, event)
        if (
            action == "acknowledge"
            and obj.volunteer.user_id != actor.pk
            and not held & {"organizer", "event_admin"}
        ):
            raise PermissionDenied
        if action in {"brief", "arrive"} and not held & {"organizer", "event_admin", "leader"}:
            raise PermissionDenied
        setattr(
            obj,
            {"acknowledge": "acknowledged_at", "brief": "briefed_at", "arrive": "arrived_at"}[action],
            timezone.now(),
        )
    elif key == "tasks":
        obj.status = "completed"
        validate_business(obj, actor)
    elif key == "speakers":
        if action == "publish":
            if not obj.publication_consent or obj.status != "confirmed":
                raise ValidationError(tr("Confirm the speaker and record publication consent first."))
            if obj.photo and (
                obj.photo.scope != "public_candidate"
                or obj.photo.scan_status != "clean"
                or obj.photo.archived_at
                or not obj.photo.content_type.startswith("image/")
            ):
                raise ValidationError(tr("Use a clean, approved public-candidate image for this speaker."))
            obj.published_snapshot = {
                "name": obj.name,
                "biography": obj.biography,
                "language": obj.language,
                "version": obj.version,
                "photo_id": str(obj.photo_id) if obj.photo_id else "",
            }
        else:
            require(actor, event, key, "approve")
            obj.published_snapshot = {}
    elif key == "team-members":
        if action == "publish":
            obj.published_snapshot = {
                "name": obj.name,
                "role": obj.role,
                "biography": obj.biography,
                "profile_url": obj.profile_url,
                "display_order": obj.display_order,
                "version": obj.version,
            }
            obj.published_at = timezone.now()
        else:
            require(actor, event, key, "approve")
            obj.published_snapshot, obj.published_at = {}, None
    elif key == "talks":
        if not all([obj.release_received, obj.fact_checked, obj.rights_cleared]):
            raise ValidationError(tr("Complete release, fact checking and rights review before approval."))
        obj.status = "approved"
    elif key == "schedule":
        if action == "publish":
            if obj.kind == "production":
                raise ValidationError(tr("Production cues stay internal."))
            if obj.talk and (obj.talk.status != "approved" or not obj.talk.speaker.published_snapshot):
                raise ValidationError(
                    tr("Approve the talk and publish its speaker before publishing this session.")
                )
            obj.published_snapshot = {
                "title": obj.title,
                "description": obj.public_description,
                "starts_at": obj.starts_at.isoformat(),
                "ends_at": obj.ends_at.isoformat(),
                "location": obj.location,
                "version": obj.version,
            }
        else:
            require(actor, event, key, "approve")
            obj.published_snapshot = {}
    elif key == "runbook":
        if action == "publish":
            obj.published_snapshot = {
                "title": obj.title,
                "instructions": obj.instructions,
                "contingency": obj.contingency,
                "cue_at": obj.cue_at.isoformat() if obj.cue_at else None,
                "audience": obj.audience,
                "department_id": str(obj.department_id) if obj.department_id else None,
                "version": obj.version,
            }
        else:
            if (
                not roles(actor, event) & {"organizer", "event_admin"}
                and not grants(actor, event).filter(role="leader", department_id=obj.department_id).exists()
            ):
                raise PermissionDenied
            obj.completed_at = timezone.now()
    elif key == "announcements":
        if action == "read":
            from communications.models import AnnouncementRead

            AnnouncementRead.objects.get_or_create(event=event, announcement=obj, user=actor)
            return obj
        obj.approved_at = timezone.now()
    elif key == "files":
        obj.archived_at = timezone.now()
    obj.version += 1
    obj.save()
    if key == "announcements" and action == "publish":
        from communications.services import queue_announcement

        queue_announcement(obj)
    if key == "schedule" and action == "publish":
        from communications.services import enqueue
        from django.conf import settings
        from admissions.services import digest

        recipients = {obj.owner.email if obj.owner else "", obj.talk.speaker.email if obj.talk else ""} - {""}
        for recipient in recipients:
            enqueue(
                event,
                recipient,
                "schedule-update",
                {
                    "name": "Event participant",
                    "status": obj.title + " · " + obj.starts_at.isoformat(),
                    "link": f"{settings.PUBLIC_BASE_URL}/e/{event.slug}/program/",
                },
                f"schedule:{obj.pk}:{obj.version}:{digest(recipient)}",
            )
    audit(event, actor, f"{key}.{action}", obj, reason=reason[:250], version=obj.version)
    return obj
