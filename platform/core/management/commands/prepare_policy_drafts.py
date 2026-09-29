"""Install review-only Turkish policy drafts without overwriting organizer work."""

import json
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from core.models import Event
from core.services import audit


class Command(BaseCommand):
    help = "Fill empty policy fields with sourced drafts; never approve or open applications."

    def add_arguments(self, parser):
        parser.add_argument("--slug", default="tedxgedik")

    @transaction.atomic
    def handle(self, *args, **options):
        event = Event.objects.select_for_update().get(slug=options["slug"])
        if (
            event.privacy_approved
            or event.policy_approved
            or event.published
            or event.volunteer_open
            or event.registration_mode != "closed"
        ):
            raise CommandError(
                "Draft installation requires unpublished, unapproved policies and closed intake."
            )
        package = json.loads(
            (settings.BASE_DIR / "content/policy-drafts.tr.json").read_text(encoding="utf-8")
        )
        if event.privacy_notice or event.terms or event.notice_version:
            self.stdout.write("Existing policy content preserved. No changes made.")
            return
        event.privacy_notice = package["privacy_notice"]
        event.terms = package["terms"]
        event.notice_version = package["version"]
        event.version += 1
        event.full_clean()
        event.save(update_fields=["privacy_notice", "terms", "notice_version", "version", "updated_at"])
        audit(
            event,
            None,
            "event.policy_drafts.prepared",
            event,
            version=package["version"],
            source="content/policy-drafts.tr.json",
            approval=False,
        )
        self.stdout.write(
            "Privacy notice, participation terms and version prepared. Approval, publication and intake unchanged."
        )
