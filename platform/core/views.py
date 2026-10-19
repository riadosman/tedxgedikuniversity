from django.utils.translation import gettext_lazy as tr
import csv
import io
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError, PermissionDenied
from django.core.paginator import Paginator
from django.db import transaction, connection
from django.db.models import Q, Count
from django.http import JsonResponse, HttpResponse, Http404
from django.shortcuts import get_object_or_404, render, redirect
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST
from .models import Event, RoleGrant
from .permissions import grants, require, can, scoped, roles
from .resources import RESOURCES
from .forms import resource_form, EventForm, ReasonForm, editable_fields
from .services import audit, locked_event, throttle
from .workflows import save_resource, action_resource


def staff_event(request, slug):
    event = get_object_or_404(Event, slug=slug)
    if not grants(request.user, event).exists():
        raise PermissionDenied
    return event


@login_required
def staff_home(request):
    first_event = Event.objects.first()
    grant = grants(request.user, first_event).first() if first_event else None
    if not grant:
        grant = (
            RoleGrant.objects.filter(user=request.user, active=True)
            .filter(Q(expires_at__isnull=True) | Q(expires_at__gt=timezone.now()))
            .first()
        )
    if not grant:
        return render(request, "staff/no_access.html", status=403)
    return redirect("dashboard", slug=grant.event.slug)


def navigation(user, event):
    held = roles(user, event)
    items = [(key, value.title) for key, value in RESOURCES.items() if can(user, event, key, held=held)]
    if can(user, event, "users"):
        items.append(("users", tr("Team accounts")))
    if can(user, event, "attendees", "export"):
        items.append(("survey-export", tr("TEDx attendee email export")))
    if can(user, event, "registrations", "edit"):
        items += [("imports", tr("CSV import / ledger")), ("roster", tr("Controlled entrance roster"))]
    return items


def staff_context(request, event, **context):
    from .navigation import workspace_groups

    items = navigation(request.user, event)
    groups = workspace_groups(
        event,
        items,
        can_settings=can(request.user, event, "event", "edit"),
        can_reports=can(request.user, event, "reports"),
    )
    route = request.resolver_match.url_name
    active_key = context.get("key") or request.resolver_match.kwargs.get("key") or route
    active_group = next(
        (group["key"] for group in groups if any(link["key"] == active_key for link in group["links"])), ""
    )
    active_group = context.get("active_group", active_group)
    return {
        "event": event,
        "navigation": items,
        "workspace_groups": groups,
        "active_group": active_group,
        "context_links": next((g["links"] for g in groups if g["key"] == active_group), []),
        "can_add_speaker": can(request.user, event, "speakers", "create"),
        "can_registrations": can(request.user, event, "registrations"),
        "can_tickets": can(request.user, event, "tickets"),
        "can_settings": can(request.user, event, "event", "edit"),
        "can_scan": can(request.user, event, "checkin", "create"),
        "can_reports": can(request.user, event, "reports"),
        "can_users": can(request.user, event, "users"),
        **context,
    }


@login_required
def workspace_group(request, slug, group):
    event = staff_event(request, slug)
    context = staff_context(request, event, active_group=group)
    selected = next((item for item in context["workspace_groups"] if item["key"] == group), None)
    if selected is None:
        raise Http404
    return render(request, "staff/group.html", {**context, "group": selected})


@login_required
def dashboard(request, slug):
    event = staff_event(request, slug)
    from operations.models import Task, Incident, RunbookItem, Contact
    from team.models import Department
    from program.models import ScheduleItem
    from communications.models import Announcement
    from admissions.models import Registration, CheckIn, Ticket
    from program.models import Speaker

    tasks = (
        scoped(Task.objects.all(), request.user, event, "tasks")
        if can(request.user, event, "tasks")
        else Task.objects.none()
    )
    incidents = scoped(Incident.objects.all(), request.user, event, "incidents")
    announcements = (
        scoped(Announcement.objects.all(), request.user, event, "announcements")
        if can(request.user, event, "announcements")
        else Announcement.objects.none()
    )
    from admissions.services import committed

    stats = [
        (tr("My visible open tasks"), tasks.exclude(status__in=["completed", "cancelled"]).count()),
        (tr("Visible open incidents"), incidents.exclude(status__in=["resolved", "closed"]).count()),
    ]
    if can(request.user, event, "reports") or can(request.user, event, "checkin", "create"):
        stats = [
            # Deleted and cancelled registrations keep anonymous rows; they are counted as cancelled tickets.
            (
                tr("Registrations"),
                Registration.objects.filter(event=event).exclude(status="cancelled").count(),
            ),
            (
                tr("Valid tickets"),
                Ticket.objects.filter(event=event, status__in=["registered", "checked_in"]).count(),
            ),
            (tr("Admitted"), CheckIn.objects.filter(event=event).count()),
            (tr("Cancelled tickets"), Ticket.objects.filter(event=event, status="cancelled").count()),
            (tr("Available capacity"), max(0, event.capacity - committed(event))),
            (tr("Remaining arrivals"), Ticket.objects.filter(event=event, status="registered").count()),
        ]
    if can(request.user, event, "speakers"):
        stats.append((tr("Speakers"), scoped(Speaker.objects.all(), request.user, event, "speakers").count()))
    from django.utils.dateparse import parse_datetime

    schedule = list(ScheduleItem.objects.filter(event=event).exclude(published_snapshot={}))
    for item in schedule:
        start = parse_datetime(item.published_snapshot["starts_at"])
        end = parse_datetime(item.published_snapshot["ends_at"])
        if start is None or end is None:
            raise ValidationError(tr("Invalid published program timestamp."))
        item.starts_at, item.ends_at = start, end
    schedule.sort(key=lambda item: item.starts_at)
    now = timezone.now()
    current = next((item for item in schedule if item.starts_at <= now < item.ends_at), None)
    upcoming = next((item for item in schedule if item.starts_at > now), None)
    departments = (
        scoped(Department.objects.all(), request.user, event, "departments")
        if can(request.user, event, "departments")
        else []
    )
    contacts = (
        scoped(Contact.objects.all(), request.user, event, "contacts")
        if can(request.user, event, "contacts")
        else []
    )
    runbook = (
        [
            readable_record(item, request.user, event, "runbook")
            for item in scoped(RunbookItem.objects.all(), request.user, event, "runbook").exclude(
                published_snapshot={}
            )[:20]
        ]
        if can(request.user, event, "runbook")
        else []
    )
    return render(
        request,
        "staff/dashboard.html",
        staff_context(
            request,
            event,
            stats=stats,
            pending_registrations=(
                scoped(Registration.objects.all(), request.user, event, "registrations")
                .filter(status="under_review")
                .count()
                if can(request.user, event, "registrations")
                else 0
            ),
            tasks=tasks.exclude(status__in=["completed", "cancelled"]).order_by("due_at")[:8],
            incidents=incidents.exclude(status__in=["resolved", "closed"])[:8],
            announcements=announcements[:5],
            schedule=schedule[:20],
            now=now,
            current_session=current,
            next_session=upcoming,
            departments=departments,
            contacts=contacts,
            runbook=runbook,
        ),
    )


def display_value(obj, column):
    from admissions.models import Attendee

    ticket = getattr(obj, "ticket", None) if isinstance(obj, Attendee) else obj
    if column == "ticket_reference":
        return ticket.reference if ticket else "—"
    if column == "attendee_email":
        return obj.attendee.email or ""
    if column == "registration_status":
        registration = getattr(obj, "registration", None)
        return registration.get_status_display() if registration else tr("No application")
    if column == "ticket_status":
        return ticket.get_status_display() if ticket else tr("No ticket")
    if column == "qr_status":
        if ticket is None:
            return tr("Inactive")
        active = ticket.status in {"registered", "checked_in"} and ticket.expires_at > timezone.now()
        return (
            tr("Active")
            if active and any(c.revoked_at is None for c in ticket.credentials.all())
            else tr("Inactive")
        )
    if column == "admission_status":
        return tr("Checked in") if ticket and hasattr(ticket, "checkin") else tr("Not admitted")
    if column == "admitted_at":
        return ticket.checkin.admitted_at if ticket and hasattr(ticket, "checkin") else "—"
    value = getattr(obj, column, "")
    display = getattr(obj, f"get_{column}_display", None)
    if display:
        value = display()
    return value if value is not None else "—"


def readable_record(obj, user, event, key):
    if (
        key == "runbook"
        and not roles(user, event) & {"organizer", "event_admin"}
        and not grants(user, event).filter(role="leader", department_id=obj.department_id).exists()
    ):
        import copy

        obj = copy.copy(obj)
        for name in ["title", "instructions", "contingency"]:
            setattr(obj, name, obj.published_snapshot.get(name, ""))
        obj.cue_at = obj.published_snapshot.get("cue_at")
        obj.owner = None
    return obj


# components/people-table.html reads these values by position.
PEOPLE_COLUMNS = {
    "attendees": (
        "name",
        "email",
        "registration_status",
        "ticket_status",
        "qr_status",
        "admission_status",
        "admitted_at",
        "phone",
    ),
    "tickets": (
        "reference",
        "attendee",
        "ticket_type",
        "status",
        "qr_status",
        "admission_status",
        "admitted_at",
    ),
}


@login_required
def resource_list(request, slug, key):
    event = staff_event(request, slug)
    resource = RESOURCES.get(key)
    if not resource:
        raise Http404
    query = scoped(resource.model.objects.all(), request.user, event, key)
    if key == "attendees":
        # Deleted and erased attendees keep anonymous rows for audit; they are not people to manage.
        query = (
            query.filter(anonymized_at__isnull=True)
            .select_related("registration", "ticket__checkin")
            .prefetch_related("ticket__credentials")
        )
    elif key == "registrations":
        query = query.filter(attendee__anonymized_at__isnull=True)
    elif key == "tickets":
        query = query.select_related("attendee", "ticket_type", "checkin").prefetch_related("credentials")
    if not query.ordered:
        query = query.order_by("-created_at", "id")
    search = request.GET.get("q", "")[:200]
    if search and resource.search:
        condition = Q()
        search_fields = (
            ("published_snapshot__title", "published_snapshot__instructions")
            if key == "runbook" and not roles(request.user, event) & {"organizer", "event_admin"}
            else resource.search
        )
        for field in search_fields:
            condition |= Q(**{field + "__icontains": search})
        query = query.filter(condition)
    status = request.GET.get("status", "")
    if key == "attendees" and status:
        query = query.filter(registration__status=status)
    if status and any(f.name == "status" for f in resource.model._meta.fields):
        query = query.filter(status=status)
    if key == "tasks" and request.GET.get("due") == "overdue":
        query = query.filter(due_at__lt=timezone.now()).exclude(status__in=["completed", "cancelled"])
    order = request.GET.get("sort", "")
    sortable = {field.name for field in resource.model._meta.fields} & set(resource.columns)
    if order.lstrip("-") in sortable:
        query = query.order_by(order)
    attendance = request.GET.get("attendance", "")
    if key in {"attendees", "tickets"} and attendance in {"yes", "no"}:
        query = query.filter(
            **{("ticket__checkin__isnull" if key == "attendees" else "checkin__isnull"): attendance == "no"}
        )
    gedik = request.GET.get("gedik", "")
    if key == "attendees" and gedik in {"yes", "no", "unknown"}:
        query = query.filter(gedik_student={"yes": True, "no": False, "unknown": None}[gedik])
    page = Paginator(query, 30).get_page(request.GET.get("page"))
    visible = [readable_record(obj, request.user, event, key) for obj in page]
    columns = PEOPLE_COLUMNS.get(key, resource.columns)
    rows = [(obj, [display_value(obj, col) for col in columns]) for obj in visible]
    return render(
        request,
        "staff/list.html",
        staff_context(
            request,
            event,
            key=key,
            resource=resource,
            rows=rows,
            page=page,
            search=search,
            status=status,
            attendance=attendance,
            gedik=gedik,
            sort=order,
            sortable=[column for column in resource.columns if column in sortable],
            status_choices=(
                RESOURCES["registrations"].model._meta.get_field("status").choices
                if key == "attendees"
                else next((f.choices for f in resource.model._meta.fields if f.name == "status"), [])
            ),
            can_create=key not in {"attendees", "registrations"}
            and (bool(resource.fields) or key == "invitations")
            and can(request.user, event, key, "create"),
            can_export=can(request.user, event, key, "export"),
        ),
    )


@login_required
def resource_detail(request, slug, key, pk):
    event = staff_event(request, slug)
    resource = RESOURCES.get(key)
    if not resource:
        raise Http404
    obj = get_object_or_404(scoped(resource.model.objects.all(), request.user, event, key), pk=pk)
    obj = readable_record(obj, request.user, event, key)
    # Never dump model.__dict__: credentials, internal columns and raw payloads stay private.
    columns = list(dict.fromkeys(resource.columns + resource.fields))
    if key == "audit":
        columns.append("metadata")
    if key == "registrations":
        columns += ["answers", "decision_note"]
    if key == "speakers" and not roles(request.user, event) & {"organizer", "speaker_manager"}:
        columns = ["name", "biography", "status"]
    if key == "talks" and not roles(request.user, event) & {"organizer", "speaker_manager"}:
        columns = ["title", "description", "technical_requirements", "status"]
    if key == "runbook" and not editable_fields(resource, request.user, event, obj):
        columns = ["title", "instructions", "contingency", "cue_at"]
    actions = []
    for action in resource.actions:
        permission = (
            "approve"
            if action
            in {
                "publish",
                "approve",
                "accepted",
                "approved",
                "waitlisted",
                "rejected",
                "under_review",
                "review",
                "interview",
                "withdraw",
            }
            else "edit"
        )
        if action == "retry":
            permission = "retry"
        if (
            action == "read"
            or (key == "runbook" and action == "acknowledge")
            or can(request.user, event, key, permission)
        ):
            actions.append(action)
    comments = obj.comments.select_related("author").all() if key in {"tasks", "incidents"} else []
    from documents.models import Document

    attachments = Document.objects.none()
    if key in {"tasks", "talks"} and can(request.user, event, "files"):
        from documents.models import Document

        attachments = scoped(Document.objects.all(), request.user, event, "files").filter(
            **{"task" if key == "tasks" else "talk": obj}
        )
    return render(
        request,
        "staff/detail.html",
        staff_context(
            request,
            event,
            key=key,
            resource=resource,
            obj=obj,
            fields=[
                (
                    col.replace("_", " ").title()
                    if col in resource.columns
                    else col.replace("_", " ").capitalize(),
                    display_value(obj, col),
                )
                for col in columns
            ],
            actions=actions,
            comments=comments,
            attachments=attachments,
            can_edit=bool(editable_fields(resource, request.user, event, obj))
            and can(request.user, event, key, "edit"),
            # Registration details live on the attendee record, so its edit form serves both lists.
            edit_url=reverse("resource-edit", args=[slug, "attendees", obj.attendee_id])
            if key == "registrations"
            and not obj.attendee.anonymized_at
            and can(request.user, event, "attendees", "edit")
            else "",
            can_speaker_photo=key == "speakers"
            and "photo" in editable_fields(resource, request.user, event, obj)
            and bool(roles(request.user, event) & {"organizer", "editor"})
            and can(request.user, event, "files", "create"),
        ),
    )


@login_required
def speaker_photo(request, slug, pk):
    from program.models import Speaker
    from documents.views import upload

    event = staff_event(request, slug)
    require(request.user, event, "speakers", "edit")
    speaker = get_object_or_404(scoped(Speaker.objects.all(), request.user, event, "speakers"), pk=pk)
    if "photo" not in editable_fields(RESOURCES["speakers"], request.user, event, speaker):
        raise PermissionDenied
    if not roles(request.user, event) & {"organizer", "editor"}:
        raise PermissionDenied
    return upload(request, event, speaker=speaker)


@login_required
def resource_edit(request, slug, key, pk=None):
    event = staff_event(request, slug)
    if key == "invitations" and pk is None:
        from admissions.invitations import create_invitation

        return create_invitation(request, event)
    resource = RESOURCES.get(key)
    if not resource or not resource.fields:
        raise Http404
    require(request.user, event, key, "edit" if pk else "create")
    obj = (
        get_object_or_404(scoped(resource.model.objects.all(), request.user, event, key), pk=pk)
        if pk
        else None
    )
    if key == "files" and pk is None:
        from documents.views import upload

        return upload(request, event)
    form = resource_form(resource, request.user, event, request.POST or None, obj)
    if request.method == "POST" and form.is_valid():
        try:
            if key == "roles":
                from .auth_views import recent_mfa

                recent_mfa(request)
            obj = save_resource(event, request.user, key, form, request.POST.get("version"))
            messages.success(request, tr("Saved."))
            return redirect("resource-detail", slug=slug, key=key, pk=obj.pk)
        except ValidationError as error:
            form.add_error(None, error)
    return render(
        request,
        "staff/form.html",
        staff_context(
            request,
            event,
            form=form,
            title=f"{tr('Edit') if pk else tr('Add')}: {resource.title}",
            obj=obj,
            key=key,
            can_upload_photo=can(request.user, event, "files", "create"),
            profile_fields=[
                form[name]
                for name in ("name", "biography", "language", "photo", "status", "publication_consent")
                if name in form.fields
            ]
            if key == "speakers"
            else [],
            advanced_fields=[
                form[name] for name in ("email", "user", "internal_notes") if name in form.fields
            ]
            if key == "speakers"
            else [],
        ),
    )


@login_required
def resource_action(request, slug, key, pk, action):
    event = staff_event(request, slug)
    form = ReasonForm(request.POST if request.method == "POST" else None)
    if action == "read" or (key == "runbook" and action == "acknowledge"):
        form.fields["reason"].required = False
    if request.method == "POST" and form.is_valid():
        try:
            if key == "privacy" and action == "anonymize":
                from .auth_views import recent_mfa

                recent_mfa(request)
            action_resource(
                event,
                request.user,
                key,
                pk,
                action,
                form.cleaned_data["reason"],
                ticket_type=form.cleaned_data.get("ticket_type"),
            )
            if key in {"attendees", "registrations"} and action == "delete":
                messages.success(request, tr("Registration deleted."))
                return redirect("resource-list", slug=slug, key=key)
            messages.success(request, tr("Action recorded."))
            return redirect("resource-detail", slug=slug, key=key, pk=pk)
        except ValidationError as error:
            form.add_error(None, error)
    deleting = key in {"attendees", "registrations"} and action == "delete"
    return render(
        request,
        "staff/form.html",
        staff_context(
            request,
            event,
            form=form,
            title=tr("Delete registration") if deleting else tr("Confirm action"),
            key=key,
            warning=tr(
                "The ticket is cancelled and its QR code stops working. Name, email, phone and plate are erased "
                "immediately and cannot be restored. The attendee is not emailed."
            )
            if deleting
            else "",
            confirm=tr("Delete this registration? This cannot be undone.") if deleting else "",
            submit_label=tr("Delete registration") if deleting else "",
        ),
    )


@login_required
def event_settings(request, slug):
    event = staff_event(request, slug)
    require(request.user, event, "event", "edit")
    form = EventForm(request.POST or None, instance=event)
    if request.method == "POST" and form.is_valid():
        try:
            from .auth_views import recent_mfa
            from admissions.services import committed, follow_event_end

            recent_mfa(request)
            with transaction.atomic():
                current = locked_event(event)
                version = request.POST.get("version", "")
                if not version.isdigit() or current.version != int(version):
                    raise ValidationError(tr("Settings changed. Reload before saving."))
                if form.instance.capacity < committed(current):
                    raise ValidationError(tr("Capacity cannot be lower than already committed tickets."))
                if form.instance.payment_mode == "paid" and form.instance.registration_mode != "closed":
                    from payments.providers import selected_provider

                    selected_provider()
                if current.entry_mode in {"manual", "reconciling"}:
                    raise ValidationError(
                        tr("Settings are frozen during manual admission and reconciliation.")
                    )
                form.instance.version += 1
                form.save()
                moved = (
                    follow_event_end(form.instance, current.ends_at) if "ends_at" in form.changed_data else 0
                )
                audit(
                    event,
                    request.user,
                    "event.settings",
                    event,
                    fields=form.changed_data,
                    tickets_moved=moved,
                )
            messages.success(request, tr("Event settings saved."))
            return redirect("event-settings", slug=slug)
        except ValidationError as error:
            form.add_error(None, error)
    return render(
        request,
        "staff/settings.html",
        staff_context(request, event, form=form, title=tr("Event & registration settings"), obj=event),
    )


@login_required
def scanner(request, slug):
    event = staff_event(request, slug)
    require(request.user, event, "checkin", "create")
    return render(
        request,
        "staff/scanner.html",
        staff_context(
            request,
            event,
            manual=can(request.user, event, "manual-checkin", "create"),
            supervisor=can(request.user, event, "entry-mode", "approve"),
        ),
    )


@login_required
def scanner_data(request, slug):
    event = staff_event(request, slug)
    require(request.user, event, "checkin", "create")
    from admissions.models import Ticket, CheckIn, ScanReceipt

    tickets = Ticket.objects.filter(event=event, status__in=["registered", "checked_in"])
    count = CheckIn.objects.filter(event=event).count()
    query = request.GET.get("q", "")[:100]
    matches = []
    if len(query) >= 2:
        try:
            throttle(f"lookup:{request.user.pk}", 60)
        except ValidationError:
            return JsonResponse({"error": "Too many searches. Wait before trying again."}, status=429)
        matches = list(
            tickets.filter(Q(reference__icontains=query) | Q(attendee__name__icontains=query)).values(
                "id", "reference", "attendee__name", "ticket_type__name", "checkin__admitted_at"
            )[:15]
        )
    from django.middleware.csrf import get_token

    return JsonResponse(
        {
            "csrf_token": get_token(request),
            "registered": tickets.count(),
            "checked_in": count,
            "remaining": tickets.filter(checkin__isnull=True).count(),
            "mode": event.entry_mode,
            "mode_label": event.get_entry_mode_display(),
            "recent": list(
                CheckIn.objects.filter(event=event)
                .order_by("-admitted_at")
                .values("ticket__attendee__name", "admitted_at")[:8]
            ),
            "rejected": ScanReceipt.objects.filter(event=event).exclude(result__code="VALID").count(),
            "matches": matches,
        }
    )


@login_required
@require_POST
def scan_api(request, slug):
    event = staff_event(request, slug)
    from admissions.services import check_in

    try:
        from admissions.contracts import ScanRequest

        data = ScanRequest.parse(request.body)
        throttle(f"scan:{request.user.pk}", 180)
        result = check_in(
            event,
            request.user,
            request_id=data.request_id,
            credential=data.credential,
            ticket_id=data.ticket_id,
            reason=data.reason,
            device=data.device,
        )
        return JsonResponse(result)
    except (ValidationError, ValueError, KeyError, TypeError) as error:
        return JsonResponse(
            {
                "code": "REQUEST_ERROR",
                "message": "; ".join(error.messages)
                if isinstance(error, ValidationError)
                else "Invalid scan request.",
            },
            status=400,
        )


@login_required
def entry_mode(request, slug):
    event = staff_event(request, slug)
    require(request.user, event, "entry-mode", "approve")
    from django import forms

    class ModeForm(ReasonForm):
        mode = forms.ChoiceField(choices=Event._meta.get_field("entry_mode").choices or [])

    form = ModeForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            from admissions.services import set_entry_mode
            from .auth_views import recent_mfa

            recent_mfa(request)
            set_entry_mode(event, request.user, **form.cleaned_data)
            messages.success(request, tr("Entry mode updated. Brief every admission desk."))
            return redirect("scanner", slug=slug)
        except ValidationError as error:
            form.add_error(None, error)
    return render(
        request,
        "staff/form.html",
        staff_context(request, event, form=form, title=tr("Change admission mode")),
    )


@login_required
@require_POST
def comment(request, slug, key, pk):
    event = staff_event(request, slug)
    if key not in {"tasks", "incidents"}:
        raise Http404
    from operations.models import Comment

    obj = get_object_or_404(scoped(RESOURCES[key].model.objects.all(), request.user, event, key), pk=pk)
    require(request.user, event, key, "edit")
    body = request.POST.get("body", "").strip()
    if not body or len(body) > 4000:
        messages.error(request, tr("Write a comment of 1–4000 characters."))
    else:
        with transaction.atomic():
            item = Comment.objects.create(
                event=event, author=request.user, body=body, **{"task" if key == "tasks" else "incident": obj}
            )
            audit(event, request.user, "comment.created", item)
    return redirect("resource-detail", slug=slug, key=key, pk=pk)


def csv_cell(value):
    text = str(value if value is not None else "")
    candidate = text
    while candidate and (candidate[0].isspace() or ord(candidate[0]) < 32):
        candidate = candidate[1:]
    return "'" + text if candidate.startswith(("=", "+", "-", "@")) else text


@login_required
def export(request, slug, key):
    event = staff_event(request, slug)
    resource = RESOURCES.get(key)
    if not resource:
        raise Http404
    require(request.user, event, key, "export")
    if request.method != "POST":
        return render(
            request,
            "staff/form.html",
            staff_context(request, event, title=tr("Export minimum operational columns"), form=ReasonForm()),
        )
    form = ReasonForm(request.POST)
    if not form.is_valid():
        return render(
            request, "staff/form.html", staff_context(request, event, title=tr("Export"), form=form)
        )
    from .auth_views import recent_mfa

    try:
        recent_mfa(request)
    except ValidationError as error:
        form.add_error(None, error)
        return render(
            request, "staff/form.html", staff_context(request, event, title=tr("Export"), form=form)
        )
    output = io.StringIO(newline="")
    writer = csv.writer(output)
    if key in {"attendees", "tickets"}:
        from admissions.models import Ticket

        writer.writerow(
            [
                "name",
                "email",
                "phone",
                "arrives_by_car",
                "vehicle_plate",
                "gedik_student",
                "ticket_id",
                "ticket_status",
                "registered_at",
                "checked_in_at",
            ]
        )
        yes_no = {True: "yes", False: "no", None: ""}
        for ticket in (
            Ticket.objects.filter(event=event).select_related("attendee").order_by("created_at").iterator()
        ):
            writer.writerow(
                [
                    csv_cell(value)
                    for value in (
                        ticket.attendee.name,
                        ticket.attendee.email or "",
                        ticket.attendee.phone,
                        yes_no[ticket.attendee.arrives_by_car],
                        ticket.attendee.vehicle_plate,
                        yes_no[ticket.attendee.gedik_student],
                        ticket.reference,
                        ticket.status.upper(),
                        ticket.created_at.isoformat(),
                        ticket.checked_in_at.isoformat() if ticket.checked_in_at else "",
                    )
                ]
            )
    else:
        writer.writerow(resource.columns)
        for obj in scoped(resource.model.objects.all(), request.user, event, key).iterator(chunk_size=100):
            writer.writerow([csv_cell(display_value(obj, col)) for col in resource.columns])
    audit(event, request.user, "report.export", key, purpose=form.cleaned_data["reason"])
    response = HttpResponse(output.getvalue(), content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="{key}.csv"'
    return response


@login_required
def reports(request, slug):
    event = staff_event(request, slug)
    require(request.user, event, "reports")
    from admissions.models import Registration, CheckIn, Ticket
    from team.models import VolunteerApplication
    from operations.models import Task, Incident

    reports = {
        "Registration": list(
            Registration.objects.filter(event=event).values("status").annotate(total=Count("id"))
        ),
        "Volunteers": list(
            VolunteerApplication.objects.filter(event=event).values("status").annotate(total=Count("id"))
        ),
        "Tasks": list(Task.objects.filter(event=event).values("status").annotate(total=Count("id"))),
        "Incidents": list(Incident.objects.filter(event=event).values("status").annotate(total=Count("id"))),
    }
    return render(
        request,
        "staff/reports.html",
        staff_context(
            request,
            event,
            reports=reports,
            checked_in=CheckIn.objects.filter(event=event).count(),
            no_shows=Ticket.objects.filter(
                event=event, status__in=["registered", "checked_in"], checkin__isnull=True
            ).count(),
        ),
    )


def health(request):
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        return JsonResponse({"status": "ok"})
    except Exception:
        return JsonResponse({"status": "unavailable"}, status=503)
