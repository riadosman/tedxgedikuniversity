"""Translate application-owned labels; event-defined questions retain their wording."""

from django.forms.renderers import DjangoTemplates
from django.utils.translation import gettext


class LocalizedFormRenderer(DjangoTemplates):
    def render(self, template_name, context, request=None):
        form = context.get("form")
        if form is not None and hasattr(form, "fields"):
            for name, field in form.fields.items():
                if not name.startswith("custom_"):
                    field.label = gettext(str(field.label or name.replace("_", " ").capitalize()))
                    if field.help_text:
                        field.help_text = gettext(str(field.help_text))
        return super().render(template_name, context, request)
