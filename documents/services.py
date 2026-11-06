from django.core.exceptions import ValidationError

from requests_app.selectors import can_view

from .models import Document
from .validators import validate_upload


def can_upload(user, req):
    if not (user.is_authenticated and user.is_active):
        return False
    if user.is_sysadmin:
        return can_view(user, req)
    if req.is_terminal:
        return False
    if req.can_edit(user):
        return True
    if req.status == "DRAFT":
        return False
    branch_staff = (
        user.role == "STAFF"
        and req.intake_by_id
        and req.current_department_id == user.department_id
        and req.status in {"SUBMITTED", "BRANCH_REVIEW"}
    )
    return (user.is_darta or user.is_chalani or user.is_pramukh or branch_staff) and can_view(user, req)


def can_delete(user, doc):
    req = doc.request
    if user.is_sysadmin:
        return True
    if doc.uploaded_by_id != user.pk or req.is_terminal:
        return False
    return req.can_edit(user) if req.requester_id == user.pk else True


def save_uploads(req, user, files, kind=Document.Kind.SUPPORTING, description=""):
    """Validate *all* files first, then store them. Raises ValidationError (list of messages)."""
    errors = []
    for f in files:
        try:
            validate_upload(f)
        except ValidationError as exc:
            errors.extend(exc.messages)
    if errors:
        raise ValidationError(errors)
    created = []
    for f in files:
        created.append(Document.objects.create(
            request=req, file=f, original_name=f.name[:255], kind=kind, description=description[:200],
            size=f.size, content_type=(getattr(f, "content_type", "") or "")[:100], uploaded_by=user,
        ))
    return created
