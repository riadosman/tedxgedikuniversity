from django.utils.translation import gettext_lazy as tr
import csv
import io
from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.http import HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from core.views import staff_event, staff_context, csv_cell
from core.permissions import require
from core.forms import ReasonForm
from core.services import audit
from .models import ImportBatch, Ticket
from .imports import preview_import, commit_import


@login_required
def imports(request, slug):
    event = staff_event(request, slug)
    require(request.user, event, "registrations", "edit")

    class ImportForm(forms.Form):
        kind = forms.ChoiceField(
            choices=[
                ("ledger", tr("Manual admission ledger")),
            ]
        )
        file = forms.FileField()

    form = ImportForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        try:
            batch = preview_import(
                event,
                request.user,
                form.cleaned_data["file"].read(1024 * 1024 + 1),
                form.cleaned_data["kind"],
            )
            return redirect("import-review", slug=slug, pk=batch.pk)
        except ValidationError as error:
            form.add_error(None, error)
    return render(
        request,
        "staff/form.html",
        staff_context(request, event, title=tr("Preview a CSV import"), form=form, multipart=True),
    )


@login_required
def import_review(request, slug, pk):
    event = staff_event(request, slug)
    require(request.user, event, "registrations", "edit")
    batch = get_object_or_404(ImportBatch, event=event, pk=pk)
    form = ReasonForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            commit_import(event, request.user, batch.pk, form.cleaned_data["reason"])
            messages.success(
                request, tr("Import committed. Repeating this batch will not repeat the changes.")
            )
            return redirect("dashboard", slug=slug)
        except ValidationError as error:
            form.add_error(None, error)
    return render(request, "staff/import.html", staff_context(request, event, batch=batch, form=form))


@login_required
def roster(request, slug):
    event = staff_event(request, slug)
    require(request.user, event, "attendees", "export")
    form = ReasonForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        output = io.StringIO(newline="")
        writer = csv.writer(output)
        writer.writerow(
            ["reference", "name", "ticket_type", "already_admitted", "ledger_id", "admitted_at", "reason"]
        )
        for ticket in Ticket.objects.filter(event=event, status__in=["registered", "checked_in"]).select_related(
            "attendee", "ticket_type", "checkin"
        ):
            writer.writerow(
                [
                    csv_cell(ticket.reference),
                    csv_cell(ticket.attendee.name),
                    csv_cell(ticket.ticket_type.name),
                    "yes" if hasattr(ticket, "checkin") else "no",
                    "",
                    "",
                    "",
                ]
            )
        audit(event, request.user, "roster.export", event, reason=form.cleaned_data["reason"])
        response = HttpResponse(output.getvalue(), content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = 'attachment; filename="controlled-admission-roster.csv"'
        return response
    return render(
        request,
        "staff/form.html",
        staff_context(request, event, title=tr("Export controlled admission roster"), form=form),
    )
