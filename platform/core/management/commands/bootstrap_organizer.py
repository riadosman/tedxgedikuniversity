import getpass
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from core.models import Event, RoleGrant
from core.services import audit


class Command(BaseCommand):
    help = "Create the initial organizer account using a hidden password prompt. No default password."

    def add_arguments(self, parser):
        parser.add_argument("username")
        parser.add_argument("email")
        parser.add_argument("--event", default="tedxgedik")

    @transaction.atomic
    def handle(self, *args, **options):
        event = Event.objects.get(slug=options["event"])
        if RoleGrant.objects.filter(event=event, role="organizer", active=True).exists():
            raise CommandError("An organizer already exists. Use authorized account administration.")
        password = getpass.getpass("New organizer password: ")
        user = get_user_model()(username=options["username"], email=options["email"])
        validate_password(password, user)
        user.set_password(password)
        user.full_clean()
        user.save()
        RoleGrant.objects.create(
            event=event, user=user, role="organizer", reason="Initial organizer bootstrap"
        )
        audit(event, user, "organizer.bootstrap", user)
        self.stdout.write("Organizer created. Enroll an authenticator at first sign-in.")
