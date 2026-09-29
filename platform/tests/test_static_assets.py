import os
from urllib.parse import parse_qs, urlsplit

from core.storage import PreviewStaticFilesStorage


def test_preview_asset_url_changes_after_edit(settings, tmp_path):
    settings.STATICFILES_DIRS = [tmp_path]
    asset = tmp_path / "preview.css"
    asset.write_text("body { color: red; }", encoding="utf-8")
    storage = PreviewStaticFilesStorage()
    original = storage.url("preview.css")
    stamp = asset.stat().st_mtime_ns
    asset.write_text("body { color: blue; }", encoding="utf-8")
    os.utime(asset, ns=(stamp + 1_000_000_000, stamp + 1_000_000_000))
    updated = storage.url("preview.css")
    assert updated != original
    assert urlsplit(updated).path == "/static/preview.css"
    assert parse_qs(urlsplit(updated).query)["v"]
    assert storage.url("missing.css") == "/static/missing.css"
