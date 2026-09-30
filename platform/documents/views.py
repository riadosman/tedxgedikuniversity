from django.utils.translation import gettext_lazy as tr
import hashlib
import shlex
import subprocess
import uuid
import zipfile
from pathlib import Path
from django import forms
from django.conf import settings
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.http import FileResponse, Http404, HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db import transaction
from core.permissions import require, scoped
from core.services import audit
from .models import Document

TYPES = {
    ".pdf": ("application/pdf", b"%PDF-"),
    ".png": ("image/png", b"\x89PNG\r\n\x1a\n"),
    ".jpg": ("image/jpeg", b"\xff\xd8\xff"),
    ".jpeg": ("image/jpeg", b"\xff\xd8\xff"),
    ".pptx": ("application/vnd.openxmlformats-officedocument.presentationml.presentation", b"PK\x03\x04"),
}


def upload(request, event, *, speaker=None):
    from core.forms import resource_form
    from core.resources import RESOURCES
    from core.views import staff_context

    require(request.user, event, "files", "create")
    if not settings.FILE_UPLOADS_ENABLED:
        return HttpResponse(
            "File uploads require persistent storage and a malware scanner. "
            "They are unavailable on this Vercel deployment.",
            status=503,
            content_type="text/plain; charset=utf-8",
        )
    form = resource_form(RESOURCES["files"], request.user, event, request.POST or None)
    form.fields["file"] = forms.FileField()
    if speaker is not None:
        form.fields["file"].widget.attrs["accept"] = "image/png,image/jpeg"
        for name in ("department", "task", "talk"):
            form.fields.pop(name, None)
        form.fields["scope"].choices = [("public_candidate", tr("Speaker photo"))]
        form.fields["scope"].initial = "public_candidate"
        form.fields["scope"].widget = forms.HiddenInput()
        form.fields["title"].initial = speaker.name
    form.files = request.FILES
    # Metadata-only ModelForm cannot validate mandatory storage fields before upload processing.
    for name, value in {
        "original_name": "pending.pdf",
        "storage_key": str(uuid.uuid4()),
        "content_type": "application/pdf",
        "size": 1,
        "sha256": "0" * 64,
        "uploader": request.user,
    }.items():
        setattr(form.instance, name, value)
    if request.method == "POST" and form.is_valid():
        path = None
        try:
            uploaded = request.FILES.get("file")
            suffix = Path(uploaded.name).suffix.lower()
            if speaker is not None and suffix not in {".png", ".jpg", ".jpeg"}:
                raise ValidationError(tr("Choose a PNG or JPEG speaker photo."))
            if suffix not in TYPES or not 0 < uploaded.size <= 25 * 1024 * 1024:
                raise ValidationError(tr("Upload a PDF, PNG, JPEG or PPTX up to 25 MB."))
            content = uploaded.read()
            mime, signature = TYPES[suffix]
            if not content.startswith(signature):
                raise ValidationError(tr("File content does not match its extension."))
            if suffix in {".png", ".jpg", ".jpeg"}:
                import io
                from PIL import Image

                with Image.open(io.BytesIO(content)) as picture:
                    if picture.format not in {"PNG", "JPEG"} or picture.width * picture.height > 25_000_000:
                        raise ValidationError(tr("Use a valid PNG/JPEG image of at most 25 megapixels."))
                    picture.verify()
            if suffix == ".pptx":
                import io

                with zipfile.ZipFile(io.BytesIO(content)) as archive:
                    names = archive.namelist()
                    if "ppt/presentation.xml" not in names or any(
                        "vbaproject" in n.lower()
                        or n.startswith(("/", "\\"))
                        or ".." in n.replace("\\", "/").split("/")
                        for n in names
                    ):
                        raise ValidationError(tr("Invalid or macro-enabled presentation."))
                    if len(names) > 5000 or sum(i.file_size for i in archive.infolist()) > 150 * 1024 * 1024:
                        raise ValidationError(tr("Expanded presentation is too large."))
            obj = form.instance
            obj.storage_key = f"{event.pk}/{uuid.uuid4().hex}{suffix}"
            path = settings.MEDIA_ROOT / obj.storage_key
            path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            path.write_bytes(content)
            path.chmod(0o600)
            obj.original_name = Path(uploaded.name).name[:180]
            obj.content_type, obj.size, obj.sha256 = mime, len(content), hashlib.sha256(content).hexdigest()
            if settings.FILE_SCAN_COMMAND:
                result = subprocess.run(
                    [*shlex.split(settings.FILE_SCAN_COMMAND), str(path)], capture_output=True, timeout=60
                )
                if result.returncode:
                    raise ValidationError(tr("The file did not pass the configured scanner."))
                obj.scan_status = "clean"
            # Without a configured scanner the file remains quarantined, even in development.
            from core.workflows import save_resource

            with transaction.atomic():
                save_resource(event, request.user, "files", form)
                if speaker is not None:
                    photo_form_class = forms.modelform_factory(type(speaker), fields=["photo"])
                    photo_form = photo_form_class({"photo": obj.pk}, instance=speaker)
                    if not photo_form.is_valid():
                        raise ValidationError(tr("The photo could not be attached."))
                    save_resource(
                        event, request.user, "speakers", photo_form, request.POST.get("speaker_version")
                    )
            messages.success(
                request,
                tr("File uploaded.")
                if obj.scan_status == "clean"
                else tr("File quarantined pending a configured malware scan."),
            )
            if speaker is not None:
                return redirect("resource-detail", slug=event.slug, key="speakers", pk=speaker.pk)
            return redirect("resource-detail", slug=event.slug, key="files", pk=obj.pk)
        except (ValidationError, ValueError, zipfile.BadZipFile, OSError, subprocess.TimeoutExpired) as error:
            if path:
                path.unlink(missing_ok=True)
            form.add_error(
                None, error if isinstance(error, ValidationError) else tr("The file could not be validated.")
            )
        except Exception:
            # A failed permission/database check must not leave an untracked private file.
            if path:
                path.unlink(missing_ok=True)
            raise
    return render(
        request,
        "staff/form.html",
        staff_context(
            request,
            event,
            title=tr("Speaker photo") if speaker else tr("Upload private file"),
            form=form,
            multipart=True,
            photo_speaker=speaker,
        ),
    )


@login_required
def download(request, slug, pk):
    from core.views import staff_event

    event = staff_event(request, slug)
    obj = get_object_or_404(
        scoped(Document.objects.all(), request.user, event, "files"),
        pk=pk,
        archived_at__isnull=True,
        scan_status="clean",
    )
    path = (settings.MEDIA_ROOT / obj.storage_key).resolve()
    if not path.is_relative_to(settings.MEDIA_ROOT.resolve()) or not path.is_file():
        raise Http404
    audit(event, request.user, "file.download", obj)
    response = FileResponse(
        path.open("rb"),
        as_attachment=True,
        filename=obj.original_name,
        content_type="application/octet-stream",
    )
    response["Cache-Control"] = "no-store, private"
    return response


def public_image(request, slug, pk):
    from core.public_views import public_event
    from program.models import Speaker

    event = public_event(slug)
    if not Speaker.objects.filter(event=event, published_snapshot__photo_id=str(pk)).exists():
        raise Http404
    obj = get_object_or_404(
        Document, event=event, pk=pk, scope="public_candidate", scan_status="clean", archived_at__isnull=True
    )
    if obj.content_type not in {"image/png", "image/jpeg"}:
        raise Http404
    path = (settings.MEDIA_ROOT / obj.storage_key).resolve()
    if not path.is_relative_to(settings.MEDIA_ROOT.resolve()) or not path.is_file():
        raise Http404
    return FileResponse(path.open("rb"), content_type=obj.content_type)
