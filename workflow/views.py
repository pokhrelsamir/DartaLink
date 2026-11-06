from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from accounts.permissions import role_required
from requests_app.selectors import visible_requests

from .models import WorkflowLog
from .services import ACTIONS, WorkflowError, perform


@login_required
@require_POST
def action(request, pk, key):
    req = get_object_or_404(visible_requests(request.user), pk=pk)  # 404 hides requests you may not see
    if key not in ACTIONS:
        messages.error(request, "Unknown action.")
        return redirect(req)
    try:
        perform(req, request.user, key, request.POST)
    except WorkflowError as exc:
        messages.error(request, str(exc))
    else:
        messages.success(request, ACTIONS[key].done)
    return redirect(req)


@role_required("SYSADMIN")
def audit_log(request):
    qs = WorkflowLog.objects.select_related("request", "actor", "to_department")
    q = request.GET.get("q", "").strip()
    act = request.GET.get("action", "")
    if q:
        qs = qs.filter(Q(request__request_number__icontains=q) | Q(actor__username__icontains=q)
                       | Q(actor__staff_id__icontains=q) | Q(remarks__icontains=q))
    if act:
        qs = qs.filter(action=act)
    qs = qs.order_by("-created_at", "-id")
    page = Paginator(qs, 20).get_page(request.GET.get("page"))
    params = request.GET.copy()
    params.pop("page", None)
    return render(request, "dashboard/audit_log.html", {
        "page": page, "q": q, "act": act, "action_keys": sorted(list(ACTIONS) + ["create", "edit"]),
        "querystring": params.urlencode(),
        "breadcrumbs": [("Administration", ""), ("Audit log", "")],
    })
