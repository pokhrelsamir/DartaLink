import logging
from email.mime.base import MIMEBase
from email import encoders
from pathlib import Path
from smtplib import SMTPException

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.db import transaction
from django.template.loader import render_to_string
from accounts.models import PRAMUKH_ROLES
from .models import DirectMessage, Notification

logger = logging.getLogger(__name__)
LOGO_CID = "nepal-telecom-logo"
MOBILE_LOGO_CID = "nepal-telecom-logo-mobile"
ROLE_LABELS = {
    "SYSADMIN": "System Administration",
    "KARYALAYA_PRAMUKH": "Office of the Karyalaya Pramukh",
    "PRABIDHIK_PRAMUKH": "Prabidhik Section",
    "LEKHA_PRAMUKH": "Lekha Section",
    "RAJASWA_PRAMUKH": "Rajaswa Section",
    "BUDGET_PRAMUKH": "Budget Section",
    "IT_PRAMUKH": "IT Section",
    "DARTA_STAFF": "Darta Registry",
    "CHALANI_STAFF": "Chalani Registry",
    "STAFF": "Requesting Section",
}
ACTION_COPY = {
    "create": (
        "A new request has been received for your section.",
        "Review the request details and supporting documents, then begin the next stage assigned to your office.",
    ),
    "submit": (
        "A request is awaiting section verification.",
        "Check the request information and documents before verifying, returning, or rejecting it.",
    ),
    "prepare_review": (
        "A request has been prepared for Pramukh review.",
        "Complete the branch-level document check and leave the request ready for verification.",
    ),
    "verify": (
        "A request has completed section verification.",
        "The request is now ready for Darta registration. The requester has also been informed.",
    ),
    "register": (
        "A request has been registered in Darta.",
        "Review the registered file and forward it to the appropriate authority when ready.",
    ),
    "forward": (
        "A request has been forwarded to your office.",
        "Review the file and add the recommendation, tippani, approval, return, or next forwarding action required at your stage.",
    ),
    "recommend": (
        "A recommendation has been added to a request.",
        "Review the updated file and continue the authority review process.",
    ),
    "tippani": (
        "A tippani has been added to a request.",
        "Review the official note and continue the request through the authority workflow.",
    ),
    "tok_aadesh": (
        "A Tok Aadesh has been issued for a request.",
        "Follow the instruction recorded in the file and proceed with the required office action.",
    ),
    "approve": (
        "A request has been approved by the Karyalaya Pramukh.",
        "The file is now ready for Chalani processing and dispatch.",
    ),
    "reject": (
        "A request has been rejected.",
        "Review the decision and the recorded reason in DartaLink for your records.",
    ),
    "return": (
        "A request has been returned for revision.",
        "Review the remarks, update the request as needed, and resubmit it when complete.",
    ),
    "process": (
        "Chalani processing has started for a request.",
        "Prepare the outward document and complete the dispatch step.",
    ),
    "dispatch": (
        "A request has been dispatched through Chalani.",
        "Verify the dispatch details and complete any remaining registry action.",
    ),
    "complete": (
        "A request has been marked completed.",
        "No further workflow action is required unless a correction or audit review is needed.",
    ),
    "cancel": (
        "A request has been cancelled by the requester.",
        "No further workflow action is required for this file.",
    ),
}


def _send_branded_email(subject, text_body, template, context, recipients, cc=None):
    html_body = render_to_string(
        f"emails/{template}.html",
        {**context, "logo_cid": LOGO_CID, "mobile_logo_cid": MOBILE_LOGO_CID},
    )
    email = EmailMultiAlternatives(
        subject,
        text_body,
        settings.DEFAULT_FROM_EMAIL,
        recipients,
        cc=cc or [],
    )
    email.attach_alternative(html_body, "text/html")

    logo_files = (
        (Path(settings.BASE_DIR) / settings.EMAIL_LOGO_PATH, LOGO_CID, "svg+xml"),
        (Path(settings.BASE_DIR) / "static" / "img" / "nt-logo.png", MOBILE_LOGO_CID, "png"),
    )
    for logo_path, content_id, subtype in logo_files:
        try:
            logo_content = logo_path.read_bytes()
        except OSError:
            logger.exception("Unable to attach the Nepal Telecom logo from %s.", logo_path)
            continue
        logo = MIMEBase("image", subtype)
        logo.set_payload(logo_content)
        encoders.encode_base64(logo)
        logo.add_header("Content-ID", f"<{content_id}>")
        logo.add_header("Content-Disposition", "inline", filename=logo_path.name)
        email.attach(logo)
    email.send(fail_silently=False)


def _activity_email_recipient(user=None):
    shared_recipient = getattr(settings, "WORKFLOW_NOTIFICATION_EMAIL", "").strip()
    if getattr(settings, "USE_EMPLOYEE_EMAILS", False) and user is not None:
        employee_email = (user.email or "").strip()
        if employee_email:
            return employee_email
    return shared_recipient


def notify(users, request, title, message="", level="info", exclude=None):
    """Create one notification per distinct active recipient (never for `exclude`)."""
    seen, rows = set(), []
    for u in users:
        if u is None or not u.is_active or u.pk in seen or (exclude and u.pk == exclude.pk):
            continue
        seen.add(u.pk)
        rows.append(Notification(recipient=u, request=request, title=title, message=message[:300], level=level))
    return Notification.objects.bulk_create(rows)


def queue_workflow_email(request, action, actor, status):
    """Send a workflow event to responsible role mailboxes after commit."""
    email_users = list(getattr(request, "_workflow_email_users", None) or [])
    if action == "create" and not email_users and request.department_id:
        email_users = list(
            request.department.members.filter(
                is_active=True, role__in=[role.value for role in PRAMUKH_ROLES]
            )
        )
    email_users.append(actor)
    recipients = {
        settings.WORKFLOW_ROLE_EMAILS.get(user.role)
        for user in email_users
        if settings.WORKFLOW_ROLE_EMAILS.get(user.role)
    }
    if not recipients:
        fallback = getattr(settings, "WORKFLOW_NOTIFICATION_EMAIL", "").strip()
        if fallback:
            recipients.add(fallback)
    cc = set(getattr(settings, "WORKFLOW_CC_EMAILS", [])) - recipients
    if not recipients:
        logger.warning("Workflow email skipped: WORKFLOW_NOTIFICATION_EMAIL is empty.")
        return

    request_number = request.request_number
    role_names = sorted({ROLE_LABELS.get(user.role, user.get_role_display()) for user in email_users})
    summary, next_step = ACTION_COPY.get(
        action,
        ("A workflow update was recorded for this request.", "Sign in to DartaLink to review the file and take any action assigned to your office."),
    )
    subject = f"DartaLink · {request_number} · {action.replace('_', ' ').title()}"
    body = (
        f"{summary}\n\n"
        f"Request: {request_number}\n"
        f"Title: {request.title}\n"
        f"Concerned office: {', '.join(role_names) or 'DartaLink workflow'}\n"
        f"Operation: {action.replace('_', ' ').title()}\n"
        f"New status: {status}\n"
        f"Performed by: {actor.display_name} ({actor.staff_id})\n"
        f"Timestamp: {request.updated_at:%d %b %Y, %H:%M %Z}\n\n"
        f"Next step: {next_step}\n\n"
        "Sign in to DartaLink to review the complete request and audit trail."
    )

    def send():
        try:
            _send_branded_email(
                subject,
                body,
                "workflow",
                {
                    "request_number": request_number,
                    "request_title": request.title,
                    "action": action.replace("_", " ").title(),
                    "status": status,
                    "actor_name": actor.display_name,
                    "actor_staff_id": actor.staff_id,
                    "updated_at": request.updated_at,
                    "summary": summary,
                    "next_step": next_step,
                    "concerned_office": ", ".join(role_names) or "DartaLink workflow",
                },
                sorted(recipients),
                sorted(cc),
            )
        except (OSError, SMTPException):
            logger.exception("Unable to send workflow email for %s.", request_number)

    transaction.on_commit(send)


def send_direct_message(sender, recipient, subject, body):
    message = DirectMessage.objects.create(
        sender=sender, recipient=recipient, subject=subject.strip(), body=body.strip()
    )
    Notification.objects.create(
        recipient=recipient,
        direct_message=message,
        title=message.subject,
        message=f"From {sender.display_name}: {message.body}"[:300],
        level="info",
    )
    email_recipient = _activity_email_recipient(recipient)
    if not email_recipient:
        logger.warning("Direct message %s has no email recipient.", message.pk)
        return message

    def send():
        try:
            text_body = (
                f"Message from {sender.display_name} ({sender.staff_id}):\n\n{message.body}\n\n"
                "Please sign in to DartaLink to view this message."
            )
            _send_branded_email(
                f"DartaLink · {message.subject}",
                text_body,
                "direct_message",
                {
                    "sender_name": sender.display_name,
                    "sender_staff_id": sender.staff_id,
                    "message_subject": message.subject,
                    "message_body": message.body,
                },
                [email_recipient],
                sorted(set(getattr(settings, "WORKFLOW_CC_EMAILS", [])) - {email_recipient}),
            )
        except (OSError, SMTPException):
            logger.exception("Unable to send direct message %s by email.", message.pk)

    transaction.on_commit(send)
    return message
