from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.shortcuts import render
from django.urls import reverse

from accounts.models import Department, User
from requests_app.models import (IN_AUTHORITY, AdministrativeRequest, Status)
from requests_app.selectors import action_queue, visible_requests
from requests_app.utils import today
from workflow.models import WorkflowLog

LIST = "/requests/"
IN_PROGRESS = [Status.SUBMITTED, Status.BRANCH_REVIEW, Status.VERIFIED, Status.REGISTERED, Status.FORWARDED, Status.UNDER_REVIEW,
               Status.APPROVED, Status.PROCESSING, Status.DISPATCHED]


def _card(label, value, url="", tone="neutral", hint=""):
    return {"label": label, "value": value, "url": url, "tone": tone, "hint": hint}


@login_required
def home(request):
    user = request.user
    visible = visible_requests(user)
    cards, quick = [], []

    if user.is_sysadmin:
        cards = [
            _card("Total requests", visible.count(), LIST),
            _card("Active users", User.objects.filter(is_active=True).count(), reverse("accounts:user_list"), "info"),
            _card("Departments", Department.objects.filter(is_active=True).count(), reverse("accounts:department_list")),
            _card("Completed", visible.filter(status=Status.COMPLETED).count(), f"{LIST}?status=COMPLETED", "ok"),
        ]
        quick = [("Add user", reverse("accounts:user_create"), "plus"),
                 ("Add department", reverse("accounts:department_create"), "building"),
                 ("View audit log", reverse("workflow:audit"), "clock"),
                 ("API documentation", "/api/docs/", "code")]
    else:
        mine = AdministrativeRequest.objects.filter(requester=user)
        cards = [
            _card("My requests", mine.count(), f"{LIST}?scope=mine"),
            _card("In progress", mine.filter(status__in=IN_PROGRESS).count(), f"{LIST}?scope=mine", "info"),
            _card("Drafts & returned", mine.filter(status__in=[Status.DRAFT, Status.RETURNED]).count(),
                  f"{LIST}?scope=mine", "warn"),
            _card("Completed", mine.filter(status=Status.COMPLETED).count(), f"{LIST}?scope=mine&status=COMPLETED", "ok"),
        ]
        quick = [("New request", reverse("requests:create"), "plus"),
                 ("Needs my action", f"{LIST}?scope=action", "bolt"),
                 ("Search requests", LIST, "search")]
        if user.is_pramukh:
            dept = user.department_id
            cards = [
                _card("Awaiting verification",
                      AdministrativeRequest.objects.filter(department=dept, status__in=[Status.SUBMITTED, Status.BRANCH_REVIEW]).exclude(requester=user).count(),
                      f"{LIST}?scope=action", "warn"),
                _card("In your inbox",
                      AdministrativeRequest.objects.filter(current_department=dept, status__in=IN_AUTHORITY).count(),
                      f"{LIST}?scope=action", "info", "forwarded to your office"),
                _card("Section requests", AdministrativeRequest.objects.filter(department=dept).exclude(status=Status.DRAFT).count(), LIST),
                _card("My requests", mine.count(), f"{LIST}?scope=mine"),
            ]
        if user.is_darta:
            cards = [
                _card("To register", visible.filter(status=Status.VERIFIED).count(), f"{LIST}?status=VERIFIED", "warn"),
                _card("To forward", visible.filter(status=Status.REGISTERED).count(), f"{LIST}?status=REGISTERED", "info"),
                _card("Registered today", AdministrativeRequest.objects.filter(darta_date=today()).count(), LIST, "ok"),
                _card("Total Darta entries", AdministrativeRequest.objects.exclude(darta_number="").count(), LIST),
            ]
        if user.role == "STAFF":
            cards = [
                _card("To prepare", visible.filter(status=Status.SUBMITTED).count(), f"{LIST}?scope=action", "warn"),
                _card("In branch review", visible.filter(status=Status.BRANCH_REVIEW).count(), f"{LIST}?scope=action", "info"),
                _card("Branch requests", visible.filter(current_department=user.department_id).count(), LIST),
                _card("My requests", mine.count(), f"{LIST}?scope=mine"),
            ]
        if user.is_chalani:
            cards = [
                _card("To process", visible.filter(status=Status.APPROVED).count(), f"{LIST}?status=APPROVED", "warn"),
                _card("Processing", visible.filter(status=Status.PROCESSING).count(), f"{LIST}?status=PROCESSING", "info"),
                _card("To complete", visible.filter(status=Status.DISPATCHED).count(), f"{LIST}?status=DISPATCHED", "info"),
                _card("Total Chalani entries", AdministrativeRequest.objects.exclude(chalani_number="").count(), LIST, "ok"),
            ]

    ids = visible.values("pk")
    dist_rows = (AdministrativeRequest.objects.filter(pk__in=ids).values("status")
                 .annotate(n=Count("pk")).order_by())
    counts = {r["status"]: r["n"] for r in dist_rows}
    biggest = max(counts.values(), default=0) or 1
    distribution = [{"label": label, "key": key, "n": counts.get(key, 0),
                     "pct": int(counts.get(key, 0) * 100 / biggest)}
                    for key, label in Status.choices if counts.get(key, 0)]

    queue = None if user.is_sysadmin else action_queue(user).order_by("-updated_at")[:8]
    recent = (WorkflowLog.objects.filter(request__in=ids).select_related("request", "actor")
              .order_by("-created_at", "-id")[:8])
    return render(request, "dashboard/home.html", {
        "cards": cards, "quick": quick, "queue": queue, "recent": recent, "distribution": distribution,
        "breadcrumbs": [("Dashboard", "")],
    })
