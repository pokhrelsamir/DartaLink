from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from accounts.models import Department
from documents.models import Document
from documents.services import can_delete, can_upload, save_uploads
from notifications.services import queue_workflow_email
from workflow.models import WorkflowLog
from workflow.services import WorkflowError, available_actions, perform

from .filters import SORTS, apply_filters
from .forms import RequestForm
from .models import PIPELINE, AdministrativeRequest, Category, Priority, Status
from .selectors import action_queue, visible_requests
from .reports import build_requests_pdf


@login_required
def request_list(request):
    user = request.user
    scope = request.GET.get("scope", "all")
    qs = visible_requests(user)
    if scope == "mine":
        qs = qs.filter(requester=user)
    elif scope == "action":
        qs = qs.filter(pk__in=action_queue(user).values("pk"))
    qs = apply_filters(qs, request.GET)
    page = Paginator(qs, 10).get_page(request.GET.get("page"))
    params = request.GET.copy()
    params.pop("page", None)
    return render(request, "requests/list.html", {
        "page": page, "scope": scope, "params": request.GET, "querystring": params.urlencode(),
        "statuses": Status.choices, "categories": Category.choices, "priorities": Priority.choices,
        "departments": Department.objects.filter(is_active=True), "sorts": list(SORTS),
        "total": page.paginator.count,
        "breadcrumbs": [("Requests", "")],
    })


def _request_queryset_for_report(request):
    qs = visible_requests(request.user)
    scope = request.GET.get("scope", "all")
    if scope == "mine":
        qs = qs.filter(requester=request.user)
    elif scope == "action":
        qs = qs.filter(pk__in=action_queue(request.user).values("pk"))
    return apply_filters(qs, request.GET)


def _filter_description(request):
    labels = []
    for key, label in (
        ("q", "Search"), ("status", "Status"), ("category", "Category"),
        ("priority", "Priority"), ("department", "Section"),
        ("date_from", "From"), ("date_to", "To"), ("sort", "Sort"),
    ):
        value = (request.GET.get(key) or "").strip()
        if value:
            labels.append(f"{label}: {value}")
    scope = request.GET.get("scope")
    if scope and scope != "all":
        labels.insert(0, f"Scope: {scope.replace('_', ' ').title()}")
    return ", ".join(labels) or "All visible requests"


@login_required
def request_report(request):
    if not request.user.is_sysadmin:
        raise PermissionDenied
    requests = list(_request_queryset_for_report(request).select_related(
        "requester", "department", "current_department",
    ))
    return render(request, "requests/report.html", {
        "requests": requests,
        "total": len(requests),
        "filter_description": _filter_description(request),
        "generated_at": timezone.localtime(),
        "list_url": f"{reverse('requests:list')}?{request.GET.urlencode()}",
        "pdf_url": f"{reverse('requests:report_pdf')}?{request.GET.urlencode()}",
        "breadcrumbs": [("Requests", reverse("requests:list")), ("Request report", "")],
    })


@login_required
def request_report_pdf(request):
    if not request.user.is_sysadmin:
        raise PermissionDenied
    requests = list(_request_queryset_for_report(request).select_related("requester", "department"))
    return build_requests_pdf(requests, _filter_description(request))


def _handle_files(request, req):
    files = request.FILES.getlist("files")
    if not files:
        return True
    try:
        save_uploads(req, request.user, files)
        return True
    except ValidationError as exc:
        for m in exc.messages:
            messages.error(request, m)
        return False


@login_required
def request_create(request):
    user = request.user
    if not user.can_create_requests:
        raise PermissionDenied
    if user.department_id is None:
        messages.error(request, "Your account has no department. Ask the administrator to assign one.")
        return redirect("dashboard:home")
    form = RequestForm(request.POST or None, intake_user=user)
    if request.method == "POST" and form.is_valid():
        files = request.FILES.getlist("files")
        # validate attachments up-front so a bad file never leaves a half-created request
        from documents.validators import validate_upload
        problems = []
        for f in files:
            try:
                validate_upload(f)
            except ValidationError as exc:
                problems.extend(exc.messages)
        if problems:
            for m in problems:
                messages.error(request, m)
        else:
            req = form.save(commit=False)
            req.requester, req.status = user, Status.DRAFT
            req.intake_by = user if user.is_darta else None
            req.department = form.cleaned_data.get("department") if user.is_darta else user.department
            req.save()
            WorkflowLog.objects.create(request=req, action="create", to_status=req.status, actor=user,
                                       from_department=user.department, remarks="Draft created")
            queue_workflow_email(req, "create", user, req.status)
            _handle_files(request, req)
            if "submit_now" in request.POST:
                try:
                    perform(req, user, "submit", {})
                    messages.success(request, f"{req.request_number} submitted.")
                except WorkflowError as exc:
                    messages.error(request, str(exc))
            else:
                messages.success(request, f"Draft {req.request_number} saved.")
            return redirect(req)
    return render(request, "requests/form.html", {
        "form": form, "mode": "create",
        "breadcrumbs": [("Requests", "/requests/"), ("New request", "")],
    })


@login_required
def request_edit(request, pk):
    req = get_object_or_404(visible_requests(request.user), pk=pk)
    if not req.can_edit(request.user):
        raise PermissionDenied
    form = RequestForm(request.POST or None, instance=req, intake_user=request.user)
    if request.method == "POST" and form.is_valid():
        form.save()
        WorkflowLog.objects.create(request=req, action="edit", from_status=req.status, to_status=req.status,
                                   actor=request.user, remarks="Details updated")
        files_ok = _handle_files(request, req)
        if "submit_now" in request.POST and files_ok:
            try:
                perform(req, request.user, "submit", {})
                messages.success(request, f"{req.request_number} submitted.")
            except WorkflowError as exc:
                messages.error(request, str(exc))
        elif files_ok:
            messages.success(request, "Changes saved.")
        return redirect(req)
    return render(request, "requests/form.html", {
        "form": form, "mode": "edit", "req": req,
        "breadcrumbs": [("Requests", "/requests/"), (req.request_number, req.get_absolute_url()), ("Edit", "")],
    })


@login_required
def request_detail(request, pk):
    req = get_object_or_404(visible_requests(request.user), pk=pk)
    user = request.user
    idx = req.stage_index
    steps = []
    for i, (label, _) in enumerate(PIPELINE):
        if idx == -1 or i > idx:
            state = "todo"
        elif i < idx:
            state = "done"
        else:
            state = "failed" if req.status == Status.REJECTED else ("done" if req.status == Status.COMPLETED else "current")
        steps.append({"label": label, "state": state})
    docs = list(req.documents.select_related("uploaded_by"))
    for d in docs:
        d.deletable = can_delete(user, d)
    return render(request, "requests/detail.html", {
        "req": req, "steps": steps,
        "actions": available_actions(req, user),
        "logs": req.logs.select_related("actor", "from_department", "to_department"),
        "annotations": req.annotations.select_related("author", "department"),
        "documents": docs, "can_upload": can_upload(user, req), "can_edit": req.can_edit(user),
        "doc_kinds": Document.Kind.choices,
        "last_return": req.logs.filter(action="return").last() if req.status == Status.RETURNED else None,
        "breadcrumbs": [("Requests", "/requests/"), (req.request_number, "")],
    })


@login_required
def approval_confirmation(request, pk):
    req = get_object_or_404(
        visible_requests(request.user).select_related(
            "requester", "department", "intake_by", "branch_verified_by", "approved_by"
        ),
        pk=pk,
    )
    confirmation_statuses = {
        Status.APPROVED: "Approved · awaiting dispatch",
        Status.PROCESSING: "Approved · processing",
        Status.DISPATCHED: "Dispatched",
        Status.COMPLETED: "Completed",
    }
    if req.status not in confirmation_statuses:
        from django.core.exceptions import PermissionDenied
        raise PermissionDenied("An approval confirmation is available after approval.")
    return render(request, "requests/approval_confirmation.html", {
        "req": req,
        "confirmation_status": confirmation_statuses[req.status],
        "breadcrumbs": [("Requests", reverse("requests:list")), (req.request_number, req.get_absolute_url()),
                        ("Approval confirmation", "")],
    })
