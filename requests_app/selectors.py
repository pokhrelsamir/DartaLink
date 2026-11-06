"""Server-side visibility rules (section-level access control)."""
from django.db.models import Exists, OuterRef, Q

from .models import (CHALANI_VISIBLE, DARTA_VISIBLE, IN_AUTHORITY, POST_REGISTRATION,
                     AdministrativeRequest, Status)

BASE_RELATED = ("requester", "department", "current_department")


def visible_requests(user):
    from workflow.models import WorkflowLog

    qs = AdministrativeRequest.objects.select_related(*BASE_RELATED)
    if not user.is_authenticated or not user.is_active:
        return qs.none()
    if user.is_sysadmin:
        return qs
    q = Q(requester=user)
    if user.is_pramukh and user.department_id:
        qs = qs.annotate(touched_by_dept=Exists(
            WorkflowLog.objects.filter(request=OuterRef("pk"), to_department=user.department_id)))
        not_draft = ~Q(status__in=[Status.DRAFT, Status.CANCELLED])
        q |= Q(department=user.department_id) & not_draft
        q |= Q(current_department=user.department_id) & not_draft
        q |= Q(touched_by_dept=True) & not_draft
        if user.is_karyalaya_pramukh:
            q |= Q(status__in=POST_REGISTRATION)
    if user.role == "STAFF" and user.department_id:
        q |= Q(current_department_id=user.department_id, status__in=[Status.SUBMITTED, Status.BRANCH_REVIEW]) & ~Q(requester=user)
    if user.is_darta:
        q |= Q(status__in=DARTA_VISIBLE)
        q |= Q(intake_by=user, status__in=[Status.SUBMITTED, Status.BRANCH_REVIEW])
    if user.is_chalani:
        q |= Q(status__in=CHALANI_VISIBLE)
    return qs.filter(q)


def can_view(user, req):
    return visible_requests(user).filter(pk=req.pk).exists()


def action_queue(user):
    """Requests currently waiting for *this* user to act (drives the 'Needs my action' scope)."""
    qs = AdministrativeRequest.objects.select_related(*BASE_RELATED)
    if not user.is_authenticated or not user.is_active or user.is_sysadmin:
        return qs.none()
    q = Q(requester=user, status__in=[Status.DRAFT, Status.RETURNED])
    if user.is_pramukh and user.department_id:
        q |= Q(department=user.department_id, status=Status.SUBMITTED) & ~Q(requester=user)
        q |= Q(department=user.department_id, status=Status.BRANCH_REVIEW) & ~Q(requester=user)
        q |= Q(current_department=user.department_id, status__in=IN_AUTHORITY)
    if user.role == "STAFF" and user.department_id:
        q |= Q(current_department=user.department_id, status=Status.SUBMITTED) & ~Q(requester=user)
    if user.is_darta:
        q |= Q(status__in=[Status.VERIFIED, Status.REGISTERED])
    if user.is_chalani:
        q |= Q(status__in=[Status.APPROVED, Status.PROCESSING, Status.DISPATCHED])
    return qs.filter(q)
