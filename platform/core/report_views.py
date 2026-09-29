from django.utils.translation import gettext_lazy as tr
import csv
import io
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.http import HttpResponse
from django.shortcuts import render
from django.utils import timezone
from admissions.models import Attendee
from .auth_views import recent_mfa
from .forms import ReasonForm
from .permissions import require
from .services import audit
from .views import staff_event, staff_context, csv_cell


@login_required
def survey_export(request, slug):
    event = staff_event(request, slug)
    require(request.user, event, "attendees", "export")
    form = ReasonForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            recent_mfa(request)
        except ValidationError as error:
            form.add_error(None, error)
        else:
            output = io.StringIO(newline="")
            writer = csv.writer(output)
            writer.writerow(["email"])
            people = Attendee.objects.filter(
                event=event, anonymized_at__isnull=True, ticket__checkin__isnull=False
            ).exclude(email=None)
            for person in people:
                writer.writerow(
                    [csv_cell(person.email)]
                )
            audit(
                event,
                request.user,
                "survey.export",
                event,
                count=people.count(),
                purpose=form.cleaned_data["reason"],
            )
            response = HttpResponse(output.getvalue(), content_type="text/csv; charset=utf-8")
            response["Content-Disposition"] = 'attachment; filename="tedx-attendee-emails.csv"'
            response["X-Export-Generated-At"] = timezone.now().isoformat()
            return response
    return render(
        request,
        "staff/form.html",
        staff_context(request, event, title=tr("Export TEDx attendee emails"), form=form),
    )
