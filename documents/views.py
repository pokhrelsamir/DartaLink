from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect
from django.views.decorators.http import require_GET, require_POST

from requests_app.selectors import visible_requests

from .models import Document
from .services import can_delete, can_upload, save_uploads


@login_required
@require_POST
def upload(request, request_pk):
    req = get_object_or_404(visible_requests(request.user), pk=request_pk)
    if not can_upload(request.user, req):
        raise PermissionDenied
    files = request.FILES.getlist("files")
    if not files:
        messages.error(request, "Choose at least one file to upload.")
    else:
        kind = request.POST.get("kind")
        kind = kind if kind in Document.Kind.values else Document.Kind.SUPPORTING
        try:
            saved = save_uploads(req, request.user, files, kind, request.POST.get("description", ""))
            messages.success(request, f"{len(saved)} document(s) uploaded.")
        except ValidationError as exc:
            for m in exc.messages:
                messages.error(request, m)
    return redirect(req.get_absolute_url())


@login_required
@require_GET
def _serve_document(request, pk, as_attachment):
    doc = get_object_or_404(Document.objects.select_related("request"), pk=pk)
    if not visible_requests(request.user).filter(pk=doc.request_id).exists():
        raise Http404
    try:
        handle = doc.file.open("rb")
    except FileNotFoundError:
        raise Http404("The stored file is missing.")
    return FileResponse(handle, as_attachment=as_attachment, filename=doc.original_name,
                        content_type=doc.content_type or "application/octet-stream")


@login_required
@require_GET
def view(request, pk):
    return _serve_document(request, pk, as_attachment=False)


@login_required
@require_GET
def download(request, pk):
    return _serve_document(request, pk, as_attachment=True)


@login_required
@require_POST
def delete(request, pk):
    doc = get_object_or_404(Document.objects.select_related("request"), pk=pk)
    if not visible_requests(request.user).filter(pk=doc.request_id).exists():
        raise Http404
    if not can_delete(request.user, doc):
        raise PermissionDenied
    req = doc.request
    doc.file.delete(save=False)
    doc.delete()
    messages.success(request, "Document removed.")
    return redirect(req.get_absolute_url())
