"""Fresh asset URLs for local previews; production uses manifest hashes."""

from pathlib import Path

from django.contrib.staticfiles import finders
from django.contrib.staticfiles.storage import StaticFilesStorage


class PreviewStaticFilesStorage(StaticFilesStorage):
    def url(self, name):
        url = super().url(name)
        source = finders.find(name)
        if not source:
            return url
        version = Path(source).stat().st_mtime_ns
        return f"{url}?v={version}"
