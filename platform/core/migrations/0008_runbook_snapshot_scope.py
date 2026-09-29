from django.db import migrations


def invalidate_unscoped_snapshots(apps, schema_editor):
    # Old snapshots lack immutable audience metadata. Republish explicitly rather than
    # infer visibility from a potentially edited draft audience.
    apps.get_model("operations", "RunbookItem").objects.exclude(published_snapshot={}).filter(
        published_snapshot__audience__isnull=True
    ).update(published_snapshot={})


class Migration(migrations.Migration):
    dependencies = [("core", "0007_event_admission_opens_at"), ("operations", "0002_runbookacknowledgment")]
    operations = [migrations.RunPython(invalidate_unscoped_snapshots, migrations.RunPython.noop)]
