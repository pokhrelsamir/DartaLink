"""The DartaLink state machine.

Every transition goes through `perform()`, which:
  1. checks the action is allowed for this user *and* this stage (server-side),
  2. validates the input,
  3. updates the request, writes a WorkflowLog row, and creates notifications,
all inside one database transaction.
"""
from dataclasses import dataclass
from typing import Callable

from django.db import transaction
from django.utils import timezone

from accounts.models import PRAMUKH_ROLES, Department, Role, User
from notifications.services import notify, queue_workflow_email
from requests_app.models import (IN_AUTHORITY, AdministrativeRequest, Sequence, Status)
from requests_app.utils import fiscal_year_label, today

from .models import Annotation, WorkflowLog


class WorkflowError(Exception):
    """Base class for workflow failures."""


class NotAllowed(WorkflowError):
    """The user may not perform this action at this stage."""


class Invalid(WorkflowError):
    """The input for the action is missing or wrong."""


# ---------------------------------------------------------------- helpers
def _registry(code):
    dept = Department.objects.filter(code=code, is_active=True).first()
    if dept is None:
        raise Invalid(f"The '{code}' registry department is missing or inactive.")
    return dept


def _heads(dept):
    if dept is None:
        return User.objects.none()
    return User.objects.filter(is_active=True, department=dept, role__in=[r.value for r in PRAMUKH_ROLES])


def _staff(role):
    return User.objects.filter(is_active=True, role=role)


def _is_requester(u, r):
    return u.pk == r.requester_id


def _is_section_head(u, r):
    return u.is_pramukh and u.department_id == r.department_id and not _is_requester(u, r)


def _is_branch_staff(u, r):
    return u.role == Role.STAFF and u.department_id == r.department_id


def _can_verify(u, r):
    if r.intake_by_id and r.status == Status.SUBMITTED:
        return False
    return _is_section_head(u, r)


def _branch_staff(dept):
    return User.objects.filter(is_active=True, department=dept, role=Role.STAFF)


def _is_authority_now(u, r):
    return bool(u.is_pramukh and u.department_id and u.department_id == r.current_department_id
                and u.department.is_authority)


def _kp_now(u, r):
    return _is_authority_now(u, r) and u.is_karyalaya_pramukh


def _can_return(u, r):
    if r.status in {Status.SUBMITTED, Status.BRANCH_REVIEW}:
        return _is_section_head(u, r)
    if r.status == Status.VERIFIED:
        return u.is_darta
    return _is_authority_now(u, r)


def _can_forward(u, r):
    return u.is_darta if r.status == Status.REGISTERED else _is_authority_now(u, r)


def _can_reject(u, r):
    return _is_section_head(u, r) if r.status in {Status.SUBMITTED, Status.BRANCH_REVIEW} else _kp_now(u, r)


# ---------------------------------------------------------------- action table
@dataclass(frozen=True)
class Spec:
    label: str
    style: str
    statuses: frozenset
    check: Callable
    done: str
    remarks: str = ""          # "", "optional" or "required"
    fields: tuple = ()
    help: str = ""


S = Status
ACTIONS = {
    "submit": Spec("Submit for verification", "primary", frozenset({S.DRAFT, S.RETURNED}), _is_requester,
                   "Request submitted.", "optional",
                   help="Your section Pramukh will verify the request before it goes to Darta."),
    "prepare_review": Spec("Prepare for Pramukh review", "primary", frozenset({S.SUBMITTED}), _is_branch_staff,
                   "Request prepared for Sakha Pramukh verification.", "optional",
                   help="Check the customer documents and prepare the request for your Sakha Pramukh."),
    "verify": Spec("Verify request", "success", frozenset({S.SUBMITTED, S.BRANCH_REVIEW}), _can_verify,
                   "Request verified and sent to Darta.", "optional",
                   help="Confirm the request is genuine and complete. It will be sent to Darta for registration."),
    "register": Spec("Register in Darta", "primary", frozenset({S.VERIFIED}), lambda u, r: u.is_darta,
                     "Registered in Darta.", "optional",
                     help="A Darta number and registration date will be assigned automatically."),
    "forward": Spec("Forward", "primary", frozenset({S.REGISTERED, S.FORWARDED, S.UNDER_REVIEW}), _can_forward,
                    "Request forwarded.", "optional", ("to_department",),
                    help="Send the request to another authority for review or decision."),
    "recommend": Spec("Add recommendation", "ghost", frozenset(IN_AUTHORITY), _is_authority_now,
                      "Recommendation recorded.", "required",
                      help="Your recommendation is recorded on the file and visible to later reviewers."),
    "tippani": Spec("Add tippani", "ghost", frozenset(IN_AUTHORITY), _is_authority_now,
                    "Tippani recorded.", "required",
                    help="A tippani is the official file note that accompanies the request."),
    "tok_aadesh": Spec("Issue Tok Aadesh", "warn", frozenset(IN_AUTHORITY), _kp_now,
                       "Tok Aadesh issued.", "required",
                       help="An instruction from the Office Head on how the request must be handled."),
    "approve": Spec("Approve", "success", frozenset(IN_AUTHORITY), _kp_now,
                    "Request approved and sent to Chalani.", "optional",
                    help="Approval sends the request to Chalani for processing and dispatch."),
    "reject": Spec("Reject", "danger", frozenset({S.SUBMITTED, S.BRANCH_REVIEW, S.FORWARDED, S.UNDER_REVIEW}), _can_reject,
                   "Request rejected.", "required",
                   help="Rejection is final. The requester is told the reason you give here."),
    "return": Spec("Return for revision", "warn",
                   frozenset({S.SUBMITTED, S.BRANCH_REVIEW, S.VERIFIED, S.FORWARDED, S.UNDER_REVIEW}), _can_return,
                   "Request returned to the requester.", "required",
                   help="The requester can edit and resubmit. Explain what has to change."),
    "process": Spec("Start processing", "primary", frozenset({S.APPROVED}), lambda u, r: u.is_chalani,
                    "Processing started.", "optional"),
    "dispatch": Spec("Register Chalani & dispatch", "success", frozenset({S.APPROVED, S.PROCESSING}),
                     lambda u, r: u.is_chalani, "Dispatched. Chalani number assigned.", "optional",
                     ("dispatched_to",), help="A Chalani number and date are assigned automatically."),
    "complete": Spec("Mark completed", "success", frozenset({S.DISPATCHED}), lambda u, r: u.is_chalani,
                     "Request completed.", "optional"),
    "cancel": Spec("Cancel request", "danger", frozenset({S.DRAFT, S.SUBMITTED, S.RETURNED}), _is_requester,
                   "Request cancelled.", "optional", help="A cancelled request cannot be reopened."),
}


def forward_targets(req):
    return Department.objects.filter(is_authority=True, is_active=True).exclude(pk=req.current_department_id)


def available_actions(req, user):
    if not (user.is_authenticated and user.is_active):
        return []
    out = []
    for key, spec in ACTIONS.items():
        if req.status in spec.statuses and spec.check(user, req):
            out.append({
                "key": key, "label": spec.label, "style": spec.style, "remarks": spec.remarks,
                "fields": spec.fields, "help": spec.help,
                "targets": forward_targets(req) if "to_department" in spec.fields else [],
            })
    return out


# ---------------------------------------------------------------- the engine
@transaction.atomic
def perform(req, user, key, data=None):
    data = data or {}
    caller_req = req
    spec = ACTIONS.get(key)
    if spec is None:
        raise Invalid("Unknown action.")
    if not (user.is_authenticated and user.is_active):
        raise NotAllowed("Your account cannot perform workflow actions.")
    req = AdministrativeRequest.objects.select_for_update().get(pk=req.pk)
    if req.status not in spec.statuses or not spec.check(user, req):
        raise NotAllowed(f"'{spec.label}' is not available for this request at its current stage.")
    remarks = (data.get("remarks") or "").strip()
    if spec.remarks == "required" and not remarks:
        raise Invalid("Remarks are required for this action.")

    old_status, from_dept_id = req.status, req.current_department_id
    to_dept = req.current_department
    now = timezone.now()
    notes = []  # (users, title, message, level)
    ref = req.request_number

    if key == "submit":
        req.submitted_at = now
        if user.is_darta:
            req.status, to_dept = Status.SUBMITTED, req.department
            notes.append((_branch_staff(req.department), "Customer request awaiting branch review",
                               f"{ref} received by Darta is ready for your document review.", "info"))
            notes.append((_heads(req.department), "Customer request awaiting preparation",
                               f"{ref} received by Darta needs branch staff preparation before verification.", "info"))
        elif user.is_pramukh:  # a Pramukh's own request needs no section verification
            req.status, to_dept = Status.VERIFIED, _registry("DT")
            notes.append((_staff(Role.DARTA_STAFF), "Request awaiting registration", f"{ref} is ready for Darta.", "info"))
        else:
            req.status, to_dept = Status.SUBMITTED, req.department
            notes.append((_heads(req.department), "Request awaiting verification",
                          f"{ref} from {user.display_name} needs your verification.", "info"))
    elif key == "prepare_review":
        req.status = Status.BRANCH_REVIEW
        to_dept = req.department
        notes.append((_heads(req.department), "Request ready for Sakha verification",
                      f"{ref} has been prepared by branch staff and is ready for your verification.", "info"))
    elif key == "verify":
        if old_status == Status.BRANCH_REVIEW:
            req.branch_verified_by, req.branch_verified_at = user, now
        req.status, to_dept = Status.VERIFIED, _registry("DT")
        notes.append((_staff(Role.DARTA_STAFF), "Request awaiting registration",
                      f"{ref} was verified by {user.display_name} and is ready for Darta.", "info"))
        notes.append(([req.requester], "Request verified", f"{ref} was verified and sent to Darta.", "ok"))
    elif key == "register":
        if not req.darta_number:
            fy = fiscal_year_label()
            req.darta_number = f"DARTA-{fy}-{Sequence.next('darta-' + fy):04d}"
        req.darta_date, req.registered_by = today(), user
        req.status, to_dept = Status.REGISTERED, (user.department or _registry("DT"))
        notes.append(([req.requester], "Request registered", f"{ref} registered as {req.darta_number}.", "ok"))
    elif key == "forward":
        raw = str(data.get("to_department") or "").strip()
        target = forward_targets(req).filter(pk=int(raw)).first() if raw.isdigit() else None
        if target is None:
            raise Invalid("Choose a valid department to forward to.")
        req.status, to_dept = Status.FORWARDED, target
        notes.append((_heads(target), "Request forwarded to you", f"{ref} was forwarded by {user.display_name}.", "info"))
        notes.append(([req.requester], "Request forwarded", f"{ref} is now with {target.name}.", "info"))
    elif key in ("recommend", "tippani", "tok_aadesh"):
        kind = {"recommend": Annotation.Kind.RECOMMENDATION, "tippani": Annotation.Kind.TIPPANI,
                "tok_aadesh": Annotation.Kind.TOK_AADESH}[key]
        Annotation.objects.create(request=req, kind=kind, text=remarks, author=user, department=user.department)
        req.status = Status.UNDER_REVIEW
        notes.append(([req.requester], "Review update", f"{kind.label} added to {ref}.", "info"))
    elif key == "approve":
        req.status, req.approved_by, req.approved_at, req.decision_remarks = Status.APPROVED, user, now, remarks
        to_dept = _registry("CH")
        notes.append(([req.requester], "Request approved", f"{ref} was approved.", "ok"))
        notes.append((_staff(Role.CHALANI_STAFF), "Approved request for Chalani", f"{ref} is ready for processing.", "info"))
    elif key == "reject":
        req.status, req.decision_remarks, to_dept = Status.REJECTED, remarks, None
        notes.append(([req.requester], "Request rejected", f"{ref} was rejected. Reason: {remarks}", "danger"))
    elif key == "return":
        req.status, to_dept = Status.RETURNED, None
        notes.append(([req.requester], "Request returned", f"{ref} needs changes: {remarks}", "warn"))
    elif key == "process":
        req.status = Status.PROCESSING
        notes.append(([req.requester], "Request in processing", f"{ref} is being processed by Chalani.", "info"))
    elif key == "dispatch":
        target = (data.get("dispatched_to") or "").strip()
        if not target:
            raise Invalid("Enter who the letter is dispatched to.")
        fy = fiscal_year_label()
        req.chalani_number = f"CHALANI-{fy}-{Sequence.next('chalani-' + fy):04d}"
        req.chalani_date, req.dispatched_to, req.dispatched_by = today(), target[:200], user
        req.status = Status.DISPATCHED
        notes.append(([req.requester], "Request dispatched", f"{ref} dispatched as {req.chalani_number}.", "ok"))
    elif key == "complete":
        req.status, req.completed_at = Status.COMPLETED, now
        notes.append(([req.requester], "Request completed", f"{ref} is complete.", "ok"))
    elif key == "cancel":
        req.status, to_dept = Status.CANCELLED, None

    req.current_department = to_dept
    req.save()
    if caller_req is not req:
        for field in ("status", "current_department_id", "darta_number", "darta_date",
                      "registered_by_id", "approved_by_id", "approved_at", "decision_remarks",
                      "branch_verified_by_id", "branch_verified_at",
                      "chalani_number", "chalani_date", "dispatched_to", "dispatched_by_id",
                      "completed_at", "submitted_at"):
            setattr(caller_req, field, getattr(req, field))
    WorkflowLog.objects.create(
        request=req, action=key, from_status=old_status, to_status=req.status, actor=user,
        from_department_id=from_dept_id, to_department=to_dept, remarks=remarks,
    )
    email_users = []
    for users, title, message, level in notes:
        email_users.extend(
            u for u in users
            if u is not None and u.is_active and (not user or u.pk != user.pk)
        )
        notify(users, req, title, message, level, exclude=user)
    req._workflow_email_users = email_users
    queue_workflow_email(req, key, user, req.status)
    return req
