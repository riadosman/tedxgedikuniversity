from django.db import migrations, models


def enforce_choices(apps, schema_editor):
    owned = {"core", "admissions", "team", "program", "operations", "communications", "documents", "payments"}
    quote = schema_editor.quote_name
    for model in apps.get_models():
        if model._meta.app_label not in owned:
            continue
        for field in model._meta.fields:
            if not isinstance(field, models.CharField) or not field.choices:
                continue
            values = [value for value, label in field.flatchoices]
            if field.blank and "" not in values:
                values.append("")
            name = f"{model._meta.db_table}_{field.name}_valid"[:63]
            placeholders = ", ".join(["%s"] * len(values))
            schema_editor.execute(
                f"ALTER TABLE {quote(model._meta.db_table)} ADD CONSTRAINT {quote(name)} CHECK ({quote(field.column)} IN ({placeholders}))",
                values,
            )


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0008_runbook_snapshot_scope"),
        ("admissions", "0003_attendee_notification_language"),
        ("team", "0003_volunteerapplication_notification_language"),
    ]
    operations = [migrations.RunPython(enforce_choices)]
