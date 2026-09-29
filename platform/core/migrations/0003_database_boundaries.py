from django.db import migrations, models


def add_boundaries(apps, schema_editor):
    models_by_table = {}
    for model in apps.get_models():
        if any(field.name == "event" for field in model._meta.fields):
            models_by_table[model._meta.db_table] = model
    for table in models_by_table:
        schema_editor.execute(
            f'ALTER TABLE "{table}" ADD CONSTRAINT "{table}_event_identity" UNIQUE (event_id, id)'
        )
    for table, model in models_by_table.items():
        for field in model._meta.fields:
            if (
                isinstance(field, models.ForeignKey)
                and field.remote_field.model._meta.db_table in models_by_table
            ):
                target = field.remote_field.model._meta.db_table
                name = f"{table}_{field.name}_event_fk"[:63]
                schema_editor.execute(
                    f'ALTER TABLE "{table}" ADD CONSTRAINT "{name}" FOREIGN KEY (event_id, "{field.column}") REFERENCES "{target}" (event_id, id) DEFERRABLE INITIALLY DEFERRED'
                )
    schema_editor.execute(
        "ALTER TABLE admissions_registration ADD CONSTRAINT registration_attendee_identity UNIQUE (event_id, id, attendee_id)"
    )
    schema_editor.execute(
        "ALTER TABLE admissions_ticket ADD CONSTRAINT ticket_registration_identity FOREIGN KEY (event_id, registration_id, attendee_id) REFERENCES admissions_registration (event_id, id, attendee_id) DEFERRABLE INITIALLY DEFERRED"
    )
    schema_editor.execute("""
        CREATE FUNCTION tedx_append_only() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN RAISE EXCEPTION 'Historical records are append-only'; END; $$;
        CREATE TRIGGER immutable_audit BEFORE UPDATE OR DELETE ON core_auditlog FOR EACH ROW EXECUTE FUNCTION tedx_append_only();
        CREATE TRIGGER immutable_admission BEFORE UPDATE OR DELETE ON admissions_checkin FOR EACH ROW EXECUTE FUNCTION tedx_append_only();
    """)


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0002_initial"),
        ("admissions", "0002_initial"),
        ("team", "0001_initial"),
        ("program", "0001_initial"),
        ("operations", "0001_initial"),
        ("documents", "0002_initial"),
        ("payments", "0001_initial"),
        ("communications", "0002_initial"),
    ]
    operations = [migrations.RunPython(add_boundaries)]
