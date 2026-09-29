"""Extract/compile Django catalogs on Windows without requiring GNU gettext tools."""

import ast
import json
import os
from pathlib import Path
import re
import sys
import polib
import django

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()


def messages() -> dict[str, set[str]]:
    from core.resources import RESOURCES

    found: dict[str, set[str]] = {"django": set(), "djangojs": set()}
    for folder in [
        "core",
        "admissions",
        "team",
        "program",
        "operations",
        "communications",
        "documents",
        "payments",
    ]:
        for path in (ROOT / folder).glob("*.py"):
            for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
                if (
                    isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Name)
                    and node.func.id in {"tr", "gettext", "gettext_lazy"}
                ):
                    if (
                        node.args
                        and isinstance(node.args[0], ast.Constant)
                        and isinstance(node.args[0].value, str)
                    ):
                        found["django"].add(node.args[0].value)
    for path in (ROOT / "templates").rglob("*.html"):
        for value in re.findall(r"\|default_ui:('([^']*)'|\"([^\"]*)\")", path.read_text(encoding="utf-8")):
            found["django"].add(ast.literal_eval(value[0]))
        for value in re.findall(
            r"{% translate (\"(?:[^\"\\]|\\.)*\"|'(?:[^'\\]|\\.)*')\s*%}", path.read_text(encoding="utf-8")
        ):
            found["django"].add(ast.literal_eval(value))
    for path in [ROOT / "static/scanner.js", ROOT / "static/app.js"]:
        for value in re.findall(r'gettext\(("(?:[^"\\]|\\.)*")\)', path.read_text(encoding="utf-8")):
            found["djangojs"].add(json.loads(value))
    for resource in RESOURCES.values():
        found["django"].add(resource.title_key)
        found["django"].update(
            value.replace("_", " ").title() for value in resource.columns + resource.actions
        )
    for resource in RESOURCES.values():
        names = set(resource.fields + resource.columns)
        for field in resource.model._meta.fields:
            if field.name in names:
                found["django"].add(str(field.verbose_name).replace("_", " ").capitalize())
                for _, label in field.flatchoices:
                    found["django"].add(str(label))
    from core.forms import EventForm, RegistrationForm, ReasonForm, VolunteerForm
    from core.models import Event

    for form in [EventForm(), RegistrationForm(Event()), ReasonForm(), VolunteerForm(Event())]:
        for name, field in form.fields.items():
            found["django"].add(str(field.label or name.replace("_", " ").capitalize()))
    for field in Event._meta.fields:
        for _, label in field.flatchoices:
            found["django"].add(str(label))
    return found


def main() -> None:
    inventory = messages()
    report = {}
    for language in ["en", "tr", "ar"]:
        folder = ROOT / "locale" / language / "LC_MESSAGES"
        folder.mkdir(parents=True, exist_ok=True)
        for domain, values in inventory.items():
            path = folder / f"{domain}.po"
            catalog = polib.pofile(str(path)) if path.exists() else polib.POFile()
            # A previously obsolete message may return. Preserve its translation
            # instead of reactivating duplicate empty entries that shadow it in MO.
            unique: dict[str, polib.POEntry] = {}
            for entry in catalog:
                if entry.msgid not in unique or (entry.msgstr and not unique[entry.msgid].msgstr):
                    unique[entry.msgid] = entry
            catalog[:] = list(unique.values())
            catalog.metadata = {
                "Content-Type": "text/plain; charset=UTF-8",
                "Language": language,
                "MIME-Version": "1.0",
                "Plural-Forms": (
                    "nplurals=6; plural=(n==0 ? 0 : n==1 ? 1 : n==2 ? 2 : n%100>=3 && n%100<=10 ? 3 : n%100>=11 && n%100<=99 ? 4 : 5);"
                    if language == "ar"
                    else "nplurals=2; plural=(n != 1);"
                ),
            }
            for value in sorted(values):
                if catalog.find(value, include_obsolete_entries=True) is None:
                    catalog.append(polib.POEntry(msgid=value, msgstr=value if language == "en" else ""))
            for entry in catalog:
                entry.obsolete = entry.msgid not in values
            catalog.save(str(path))
            catalog.save_as_mofile(str(path.with_suffix(".mo")))
            report[f"{language}/{domain}"] = {
                "messages": len(values),
                "untranslated": sum(not catalog.find(value).msgstr for value in values),
            }
    (ROOT / "locale/coverage.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report))
    if "--check" in sys.argv and any(item["untranslated"] for item in report.values()):
        raise SystemExit("Untranslated application messages remain.")


if __name__ == "__main__":
    main()
