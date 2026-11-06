import datetime

from django.db.models import Q

from .models import Category, Priority, Status

SORTS = {
    "newest": "-created_at", "oldest": "created_at",
    "number": "request_number", "-number": "-request_number",
    "updated": "-updated_at", "status": "status",
}


def _date(value):
    try:
        return datetime.date.fromisoformat(value)
    except (TypeError, ValueError):
        return None


def apply_filters(qs, params):
    """Shared by the HTML list view and the REST API (`params` is a QueryDict / dict)."""
    get = lambda k: (params.get(k) or "").strip()  # noqa: E731
    q = get("q")
    if q:
        qs = qs.filter(
            Q(request_number__icontains=q) | Q(title__icontains=q) | Q(description__icontains=q)
            | Q(darta_number__icontains=q) | Q(chalani_number__icontains=q)
            | Q(requester__first_name__icontains=q) | Q(requester__last_name__icontains=q)
            | Q(requester__staff_id__icontains=q)
        )
    if get("status") in Status.values:
        qs = qs.filter(status=get("status"))
    if get("category") in Category.values:
        qs = qs.filter(category=get("category"))
    if get("priority") in Priority.values:
        qs = qs.filter(priority=get("priority"))
    for field in ("department", "current_department", "requester"):
        val = get(field)
        if val.isdigit():
            qs = qs.filter(**{f"{field}_id": int(val)})
    start, end = _date(get("date_from")), _date(get("date_to"))
    if start:
        qs = qs.filter(created_at__date__gte=start)
    if end:
        qs = qs.filter(created_at__date__lte=end)
    return qs.order_by(SORTS.get(get("sort"), "-created_at"), "-id")
