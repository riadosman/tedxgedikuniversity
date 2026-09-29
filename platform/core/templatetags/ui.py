from django import template
from django.forms.boundfield import BoundField
from django.utils.translation import gettext
from django.utils.dateparse import parse_datetime
from django.utils.formats import date_format
from django.utils.timezone import localtime, is_aware

register = template.Library()


@register.simple_tag(takes_context=True)
def query_update(context, **changes):
    query = context["request"].GET.copy()
    for key, value in changes.items():
        if value is None:
            query.pop(key, None)
        else:
            query[key] = str(value)
    return "?" + query.urlencode()


@register.filter
def ui(value: object) -> str:
    """Translate application labels only; never apply to attendee/event content."""
    return gettext(str(value).replace("_", " ").title())


@register.filter
def default_ui(value: object, fallback: str) -> object:
    return value if value else gettext(fallback)


@register.filter
def column_label(columns: tuple[str, ...], position: int) -> str:
    return ui(columns[position])


@register.filter
def status_tone(value: object) -> str:
    """Presentation only: bounded CSS class; labels always remain visible."""
    label = str(value).casefold()
    groups = {
        "success": ("registered", "checked_in", "confirmed", "approved", "completed", "accepted", "resolved", "ready", "clean"),
        "warning": ("pending", "review", "under_review", "waitlisted", "blocked", "high", "in_progress"),
        "error": ("critical", "cancelled", "rejected", "expired", "failed", "overdue"),
    }
    for tone, statuses in groups.items():
        if any(
            label in (status, gettext(status.replace("_", " ").title()).casefold()) for status in statuses
        ):
            return tone
    return "neutral"


@register.filter
def program_time(value: object) -> str:
    """Render approved snapshot time without consulting unpublished model fields."""
    try:
        parsed = parse_datetime(str(value))
    except ValueError:
        return str(value)
    if parsed is None:
        return str(value)
    return date_format(localtime(parsed) if is_aware(parsed) else parsed, "H:i")


@register.filter
def localized_label(field: BoundField) -> str:
    # Shared field rendering bypasses Form.render(), so localize before label_tag.
    # Custom event questions must retain organizer-supplied wording.
    if not field.name.startswith("custom_"):
        field.label = gettext(str(field.label))
    if field.name in {"name", "email"}:
        field.field.widget.attrs.setdefault("autocomplete", field.name)
    if field.name == "email":
        field.field.widget.attrs.setdefault("inputmode", "email")
    return field.label_tag()


@register.filter
def localized_name(field: BoundField) -> str:
    return str(field.label) if field.name.startswith("custom_") else gettext(str(field.label))


@register.filter
def human_value(value: object) -> object:
    """Translate boolean display values without altering exports or organizer content."""
    from django.template.defaultfilters import yesno

    return yesno(value) if isinstance(value, bool) else value
