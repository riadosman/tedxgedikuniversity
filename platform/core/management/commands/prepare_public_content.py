"""Install source-backed trilingual draft copy without publishing or opening intake."""

import json
import re
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from core.models import Event, Page
from core.services import audit


class Command(BaseCommand):
    help = "Prepare English/Turkish/Arabic public drafts; preserve organizer edits and publication state."

    def add_arguments(self, parser):
        parser.add_argument("--slug", default="tedxgedik")

    @transaction.atomic
    def handle(self, *args, **options):
        event = Event.objects.select_for_update().filter(slug=options["slug"]).first()
        if event is None:
            raise CommandError("Import the source-backed event first.")
        package = json.loads((settings.BASE_DIR / "content/event-pages.json").read_text(encoding="utf-8"))
        source = settings.ROOT_DIR / "docs/technology-discovery/01-event-facts-and-sources.md"
        original = source.read_text(encoding="utf-8") if source.exists() else ""
        legacy = dict(re.findall(r"^\| (F08|F11) \| (.*?) \|", original, re.M))
        changed = 0
        for key, locales in package["pages"].items():
            for language, (title, body) in locales.items():
                page, created = Page.objects.get_or_create(
                    event=event,
                    key=key,
                    language=language,
                    defaults={"title": title, "body": body, "source": package["source"]},
                )
                if created:
                    audit(event, None, "content.draft.created", page, language=language)
                    changed += 1
                elif (
                    language == "en"
                    and key in {"about", "theme"}
                    and not page.published_at
                    and not page.published_snapshot
                    and page.body == legacy.get("F08" if key == "about" else "F11")
                ):
                    page.title, page.body, page.source = title, body, package["source"]
                    page.save()
                    audit(event, None, "content.draft.expanded", page, language=language)
                    changed += 1
        event.enabled_languages = list(dict.fromkeys([*event.enabled_languages, "en", "tr", "ar"]))
        event.save()
        self.stdout.write(
            f"Prepared {changed} draft pages. Existing edits preserved; publication/intake unchanged."
        )
