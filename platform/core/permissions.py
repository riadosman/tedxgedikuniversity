"""Deny-by-default event and object authorization. Never union scopes across roles."""

from django.utils.translation import gettext_lazy as tr
from typing import TypeVar
from django.contrib.auth.models import User, AnonymousUser

from django.core.exceptions import PermissionDenied
from django.db.models import Q, Model, QuerySet
from django.utils import timezone
from .models import RoleGrant, Event

ScopedModel = TypeVar("ScopedModel", bound=Model)

ADMIN = {
    "invitations",
    "attendees",
    "registrations",
    "tickets",
    "ticket-types",
    "volunteers",
    "applications",
    "memberships",
    "shifts",
    "assignments",
    "tasks",
    "dependencies",
    "incidents",
    "announcements",
    "runbook",
    "contacts",
    "files",
}
PROGRAM = {"speakers", "talks", "rehearsals", "schedule"}
READ_ONLY = {"audit", "notifications", "orders", "checkins"}


def grants(user: User | AnonymousUser, event: Event) -> QuerySet[RoleGrant]:
    if not user.is_authenticated or not user.is_active:
        return RoleGrant.objects.none()
    return RoleGrant.objects.filter(user=user, user__is_active=True, event=event, active=True).filter(
        Q(expires_at__isnull=True) | Q(expires_at__gt=timezone.now())
    )


def roles(user: User | AnonymousUser, event: Event) -> set[str]:
    return set(grants(user, event).values_list("role", flat=True))


def can(
    user: User | AnonymousUser,
    event: Event,
    resource: str,
    action: str = "view",
    held: set[str] | None = None,
) -> bool:
    held = roles(user, event) if held is None else held
    if not held:
        return False
    if resource in {"attendees", "registrations", "invitations"} and action == "create":
        return False
    if resource == "notifications" and action == "retry":
        return bool(held & {"organizer", "event_admin", "technology"})
    if "organizer" in held:
        return action != "delete" and not (resource in READ_ONLY and action not in {"view", "export"})
    if action == "delete":
        return False
    if resource in {"checkin", "manual-checkin"}:
        return bool(held & {"event_admin", "checkin"}) and (
            resource != "manual-checkin" or "event_admin" in held
        )
    if resource == "entry-mode":
        return False
    if resource == "departments" and "leader" in held and action == "edit":
        return True
    if resource == "runbook" and action == "view":
        return True
    if resource == "reports":
        return "event_admin" in held or ("finance" in held and action == "view")
    if resource == "checkins":
        return "event_admin" in held and action in {"view", "export"}
    if resource in {"event", "departments", "pages"} and action == "view" and "event_admin" in held:
        return True
    if resource in ADMIN and "event_admin" in held:
        return action in {"view", "create", "edit", "approve", "export"}
    if resource in PROGRAM and "speaker_manager" in held:
        return action in {"view", "create", "edit"}
    if resource == "pages" and "editor" in held:
        return action in {"view", "create", "edit"}
    if resource == "files" and held & {"speaker_manager", "editor", "leader"}:
        return action in {"view", "create", "edit"}
    if (
        resource
        in {
            "departments",
            "memberships",
            "volunteers",
            "shifts",
            "assignments",
            "tasks",
            "dependencies",
            "incidents",
            "runbook",
            "contacts",
        }
        and "leader" in held
    ):
        return action == "view" or (
            resource in {"shifts", "assignments", "tasks", "dependencies", "incidents", "runbook"}
            and action in {"create", "edit"}
        )
    if (
        resource in {"tasks", "incidents", "assignments", "volunteers", "runbook", "announcements", "files"}
        and "volunteer" in held
    ):
        return (
            action == "view"
            or (resource in {"tasks", "incidents", "volunteers", "assignments"} and action == "edit")
            or (resource == "incidents" and action == "create")
        )
    if resource == "incidents":
        return action in {"view", "create"} or ("technology" in held and action == "edit")
    if resource == "tasks":
        return action in {"view", "edit"}
    if resource == "announcements":
        return action == "view"
    if resource in {"speakers", "talks", "rehearsals"} and "speaker" in held:
        return action == "view" or (resource in {"speakers", "talks"} and action == "edit")
    if resource == "orders" and "finance" in held:
        return action in {"view", "export"}
    if resource == "notifications" and held & {"event_admin", "technology"}:
        return action == "view"
    if resource == "audit":
        return action == "view"
    return False


def require(user: User | AnonymousUser, event: Event, resource: str, action: str = "view") -> None:
    if not can(user, event, resource, action):
        raise PermissionDenied(tr("Your account is not authorized for this action."))


def scoped(
    queryset: QuerySet[ScopedModel], user: User | AnonymousUser, event: Event, resource: str
) -> QuerySet[ScopedModel]:
    if isinstance(user, AnonymousUser):
        raise PermissionDenied
    require(user, event, resource)
    qs = queryset.filter(event=event)
    held = roles(user, event)
    if "organizer" in held:
        return qs
    if "event_admin" in held and resource == "files":
        return qs.exclude(scope__in=["speaker", "public_candidate"]).filter(archived_at__isnull=True)
    if "event_admin" in held and resource in ADMIN | {"departments", "event", "pages"}:
        return qs
    if "event_admin" in held and resource == "checkins":
        return qs
    if "speaker_manager" in held and resource in PROGRAM:
        return qs
    if resource == "pages" and "editor" in held:
        return qs
    leader_depts = grants(user, event).filter(role="leader").values_list("department_id", flat=True)
    from team.models import Membership

    own_depts = Membership.objects.filter(event=event, volunteer__user=user, active=True).values_list(
        "department_id", flat=True
    )
    if resource == "departments":
        return qs.filter(pk__in=leader_depts)
    if resource == "volunteers":
        return qs.filter(
            Q(user=user) | Q(memberships__department_id__in=leader_depts, memberships__active=True)
        ).distinct()
    if resource == "memberships":
        return qs.filter(Q(volunteer__user=user) | Q(department_id__in=leader_depts))
    if resource == "assignments":
        return qs.filter(Q(volunteer__user=user) | Q(shift__department_id__in=leader_depts))
    if resource == "tasks":
        return qs.filter(Q(owner=user) | Q(department_id__in=leader_depts))
    if resource == "dependencies":
        return qs.filter(task__department_id__in=leader_depts)
    if resource == "incidents":
        cond = Q(reporter=user) | Q(assigned_to=user) | Q(department_id__in=leader_depts)
        if "technology" in held:
            cond |= Q(category="technical")
        return qs.filter(cond)
    if resource == "runbook":
        return qs.filter(
            Q(department_id__in=leader_depts)
            | (
                Q(published_snapshot__isnull=False)
                & ~Q(published_snapshot={})
                & (
                    Q(published_snapshot__audience="staff")
                    | Q(
                        published_snapshot__audience="department",
                        published_snapshot__department_id__in=[str(pk) for pk in own_depts],
                    )
                )
            )
        )
    if resource in {"shifts", "contacts"}:
        return qs.filter(department_id__in=leader_depts)
    if resource == "announcements":
        condition = Q(audience="staff") | Q(
            audience="department", department_id__in=list(leader_depts) + list(own_depts)
        )
        for role, audience in [
            ("leader", "leaders"),
            ("volunteer", "volunteers"),
            ("checkin", "checkin"),
            ("speaker", "speakers"),
            ("organizer", "organizers"),
        ]:
            if role in held:
                condition |= Q(audience=audience)
        return qs.filter(condition, approved_at__isnull=False, publish_at__lte=timezone.now())
    if resource == "files":
        condition = Q(scope="department", department_id__in=leader_depts) | Q(scope="task", task__owner=user)
        if "speaker_manager" in held:
            condition |= Q(scope="speaker")
        if "editor" in held:
            condition |= Q(scope="public_candidate", uploader=user)
        return qs.filter(condition, archived_at__isnull=True)
    if resource == "speakers":
        return qs.filter(user=user)
    if resource == "talks":
        return qs.filter(speaker__user=user)
    if resource == "rehearsals":
        return qs.filter(talk__speaker__user=user)
    if resource == "audit":
        return qs.filter(actor=user)
    if resource in {"orders", "notifications"}:
        return qs
    return qs.none()
