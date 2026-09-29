"""Task-based presentation of existing permission-filtered routes."""

from django.urls import reverse
from django.utils.translation import gettext_lazy as tr

GROUPS = (
    (
        "people",
        tr("Attendees & tickets"),
        tr("Registration, tickets and arrival in one place."),
        (
            "attendees",
            "registrations",
            "tickets",
            "checkins",
            "invitations",
            "ticket-types",
            "imports",
            "roster",
        ),
    ),
    ("speakers", tr("Speakers"), tr("Prepare speaker profiles and manage their publication."), ("speakers",)),
    (
        "event",
        tr("Event"),
        tr("Event information, public content and the program."),
        ("pages", "schedule", "talks", "rehearsals", "announcements"),
    ),
    (
        "team",
        tr("Team & operations"),
        tr("People, responsibilities and the work behind the event."),
        (
            "applications",
            "volunteers",
            "departments",
            "memberships",
            "shifts",
            "assignments",
            "tasks",
            "dependencies",
            "incidents",
            "runbook",
            "contacts",
            "files",
        ),
    ),
    (
        "settings",
        tr("Settings"),
        tr("Accounts, reporting and advanced administration."),
        ("users", "roles", "templates", "notifications", "privacy", "audit", "orders", "survey-export"),
    ),
)


def workspace_groups(event, items, *, can_settings=False, can_reports=False):
    available = dict(items)
    groups = []
    for key, label, description, members in GROUPS:
        links = [
            {
                "key": member,
                "label": available[member],
                "url": reverse("resource-list", args=[event.slug, member]),
            }
            for member in members
            if member in available
        ]
        if key == "event" and can_settings:
            links.insert(
                0,
                {
                    "key": "event-settings",
                    "label": tr("Event information"),
                    "url": reverse("event-settings", args=[event.slug]),
                },
            )
            links.append(
                {
                    "key": "preview",
                    "label": tr("Preview website"),
                    "url": reverse("preview", args=[event.slug]),
                }
            )
        if key == "settings" and can_reports:
            links.insert(
                0, {"key": "reports", "label": tr("Reports"), "url": reverse("reports", args=[event.slug])}
            )
        if links:
            url = (
                links[0]["url"]
                if key in {"people", "speakers", "event"}
                else reverse("workspace-group", args=[event.slug, key])
            )
            groups.append(
                {"key": key, "label": label, "description": description, "links": links, "url": url}
            )
    return groups
