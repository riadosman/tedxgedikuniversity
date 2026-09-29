from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0005_accountinvitation"),
        ("team", "0002_department_notes_department_readiness_and_more"),
        ("operations", "0002_runbookacknowledgment"),
    ]
    operations = [
        migrations.RunSQL("""
        ALTER TABLE team_applicationtoken ADD CONSTRAINT application_token_event_fk
        FOREIGN KEY (event_id, application_id) REFERENCES team_volunteerapplication(event_id, id) DEFERRABLE INITIALLY DEFERRED;
        ALTER TABLE operations_runbookacknowledgment ADD CONSTRAINT runbook_ack_event_fk
        FOREIGN KEY (event_id, item_id) REFERENCES operations_runbookitem(event_id, id) DEFERRABLE INITIALLY DEFERRED;
    """)
    ]
