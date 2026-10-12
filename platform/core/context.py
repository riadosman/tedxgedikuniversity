# Announcements are published on Instagram; LinkedIn is where attendees mention the event.
INSTAGRAM_URL = "https://www.instagram.com/tedx_gedik_uni/"
INSTAGRAM_HANDLE = "@tedx_gedik_uni"
LINKEDIN_URL = "https://www.linkedin.com/company/tedx-gedik-university/"


def site_context(request):
    from django.conf import settings
    from .models import Event

    slug = request.resolver_match.kwargs.get("slug") if request.resolver_match else None
    event = Event.objects.filter(slug=slug).first() if slug else Event.objects.filter(published=True).first()
    if not event and settings.DEBUG and settings.LOCAL_EVENT_PREVIEW and not settings.PRODUCTION:
        event = Event.objects.first()
    if not slug and request.user.is_authenticated:
        event = Event.objects.filter(rolegrant__user=request.user, rolegrant__active=True).first() or event
    language_query = request.GET.copy()
    language_query.pop("lang", None)
    language_next = request.path + ("?" + language_query.urlencode() if language_query else "")
    return {
        "language_next": language_next,
        "event_preview": getattr(request, "event_preview", False),
        "interface_languages": list(settings.LANGUAGES),
        "instagram_url": INSTAGRAM_URL,
        "instagram_handle": INSTAGRAM_HANDLE,
        "linkedin_url": LINKEDIN_URL,
    }
