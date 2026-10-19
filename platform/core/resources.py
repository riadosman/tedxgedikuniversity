"""Focused operations UI definitions. Fields are explicit, never '__all__'."""

from dataclasses import dataclass
from django.utils.translation import gettext
from admissions import models as a
from communications import models as c
from documents.models import Document
from operations import models as o
from payments.models import Order
from program import models as p
from team import models as t
from . import models as m


@dataclass(frozen=True)
class Resource:
    model: type
    title_key: str
    fields: tuple[str, ...]
    columns: tuple[str, ...]
    search: tuple[str, ...] = ()
    actions: tuple[str, ...] = ()

    @property
    def title(self) -> str:
        return gettext(self.title_key)


def resource(model, title, fields, columns, search="", actions=""):
    return Resource(
        model,
        title,
        tuple(fields.split()),
        tuple(columns.split()),
        tuple(search.split()),
        tuple(actions.split()),
    )


RESOURCES = {
    "invitations": resource(m.Invitation, "Attendee invitations", "", "email expires_at used_at", "email"),
    "pages": resource(
        m.Page,
        "Public pages & FAQs",
        "key language title body source",
        "title language published_at",
        "title body",
        "publish",
    ),
    "attendees": resource(
        a.Attendee,
        "Attendees",
        "name email phone gedik_student arrives_by_car vehicle_plate",
        "name email phone gedik_student vehicle_plate ticket_reference ticket_status created_at admitted_at",
        "name email phone vehicle_plate ticket__reference",
        "delete",
    ),
    "registrations": resource(
        a.Registration,
        "Registrations",
        "",
        "attendee status created_at",
        "attendee__name attendee__email",
        "delete",
    ),
    "tickets": resource(
        a.Ticket,
        "Tickets",
        "",
        "reference attendee attendee_email status created_at checked_in_at cancelled_at",
        "reference attendee__name attendee__email",
        "cancel rotate",
    ),
    "checkins": resource(
        a.CheckIn,
        "Admission history",
        "",
        "ticket actor admitted_at source",
        "ticket__reference ticket__attendee__name",
    ),
    "ticket-types": resource(a.TicketType, "Ticket types", "name code enabled", "name code enabled", "name"),
    "applications": resource(
        t.VolunteerApplication,
        "Volunteer applications",
        "internal_notes",
        "name email status preferred_department",
        "name email skills",
        "review interview accepted rejected waitlisted",
    ),
    "team-members": resource(
        t.TeamMember,
        "Public team",
        "name role biography profile_url display_order",
        "name role display_order published_at",
        "name role",
        "publish withdraw",
    ),
    "volunteers": resource(
        t.Volunteer,
        "Volunteers",
        "user name email skills languages availability active",
        "name email active",
        "name email skills",
    ),
    "departments": resource(
        t.Department,
        "Departments",
        "name description responsibilities active readiness notes",
        "name readiness active",
        "name",
    ),
    "memberships": resource(
        t.Membership,
        "Department memberships",
        "department volunteer supervisor responsibilities active",
        "department volunteer supervisor active",
        "volunteer__name department__name",
    ),
    "shifts": resource(
        t.Shift,
        "Shifts",
        "department title starts_at ends_at location instructions",
        "title department starts_at ends_at",
        "title",
    ),
    "assignments": resource(
        t.ShiftAssignment,
        "Shift assignments",
        "shift volunteer status",
        "volunteer shift status acknowledged_at briefed_at arrived_at",
        "volunteer__name shift__title",
        "acknowledge brief arrive",
    ),
    "tasks": resource(
        o.Task,
        "Tasks",
        "title description department owner priority status due_at acceptance",
        "title department owner priority status due_at",
        "title description",
        "complete",
    ),
    "dependencies": resource(o.TaskDependency, "Task dependencies", "task depends_on", "task depends_on"),
    "speakers": resource(
        p.Speaker,
        "Speakers",
        "user name email biography language photo internal_notes status publication_consent",
        "name status language",
        "name",
        "publish withdraw",
    ),
    "talks": resource(
        p.Talk,
        "Talk preparation",
        "speaker title description technical_requirements fact_check_notes rights_notes release_received fact_checked rights_cleared status",
        "title speaker status",
        "title speaker__name",
        "approve",
    ),
    "rehearsals": resource(
        p.Rehearsal,
        "Rehearsals",
        "talk starts_at ends_at location notes completed",
        "talk starts_at location completed",
        "talk__title",
    ),
    "schedule": resource(
        p.ScheduleItem,
        "Program & production schedule",
        "title kind talk starts_at ends_at location owner internal_cues public_description",
        "title kind starts_at ends_at",
        "title",
        "publish withdraw",
    ),
    "incidents": resource(
        o.Incident,
        "Incidents",
        "title description category severity department assigned_to status resolution",
        "title severity status assigned_to",
        "title description",
    ),
    "announcements": resource(
        c.Announcement,
        "Announcements",
        "title body priority audience department publish_at",
        "title priority audience publish_at",
        "title body",
        "publish read",
    ),
    "runbook": resource(
        o.RunbookItem,
        "Event-day runbook",
        "title cue_at department owner instructions contingency audience",
        "title cue_at department owner completed_at",
        "title instructions",
        "publish done acknowledge",
    ),
    "contacts": resource(
        o.Contact,
        "Operational contacts",
        "name responsibility phone email department notes",
        "name responsibility phone",
        "name responsibility",
    ),
    "files": resource(
        Document,
        "Private files",
        "title department task talk scope",
        "title scope scan_status size",
        "title",
        "archive",
    ),
    "templates": resource(
        c.NotificationTemplate, "Email templates", "key language subject body", "key language subject", "key"
    ),
    "notifications": resource(
        c.Notification,
        "Email delivery",
        "",
        "template_key status attempts next_attempt_at last_error_code",
        "template_key",
        "retry",
    ),
    "roles": resource(
        m.RoleGrant,
        "Roles & permissions",
        "user role department active expires_at reason",
        "user role department active expires_at",
        "user__username",
    ),
    "audit": resource(m.AuditLog, "Audit trail", "", "created_at actor action target", "action target"),
    "privacy": resource(
        m.PrivacyRequest,
        "Privacy requests",
        "email kind status resolution hold_until",
        "email kind status hold_until",
        "email",
        "anonymize",
    ),
    "orders": resource(
        Order,
        "Payment orders",
        "",
        "provider provider_reference amount_minor currency status",
        "provider_reference",
    ),
}

MODEL_RESOURCES = {r.model: key for key, r in RESOURCES.items()}
