from django.urls import reverse
from django.core import mail
from django.test import override_settings

from core.testutils import DartaTestCase, make_request
from requests_app.models import Status
from workflow.services import perform

from .models import Notification
from .models import DirectMessage
from .services import notify


class NotificationEventTests(DartaTestCase):
    @override_settings(
        EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
        WORKFLOW_NOTIFICATION_EMAIL="poksamir@gmail.com",
        WORKFLOW_CC_EMAILS=["poksamir6@gmail.com"],
        WORKFLOW_ROLE_EMAILS={
            "IT_PRAMUKH": "it-chief@example.test",
            "STAFF": "requester@example.test",
        },
        USE_EMPLOYEE_EMAILS=False,
        DEFAULT_FROM_EMAIL="DartaLink <noreply@example.test>",
    )
    def test_workflow_operation_sends_email_after_commit(self):
        req = make_request(self.staff)
        with self.captureOnCommitCallbacks(execute=True):
            perform(req, self.staff, "submit")
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(
            mail.outbox[0].to,
            ["it-chief@example.test", "requester@example.test"],
        )
        self.assertEqual(mail.outbox[0].cc, ["poksamir6@gmail.com"])
        self.assertEqual(mail.outbox[0].attachments[0].get_content_type(), "image/svg+xml")
        self.assertEqual(mail.outbox[0].attachments[1].get_content_type(), "image/png")
        self.assertIn("cid:nepal-telecom-logo", mail.outbox[0].alternatives[0][0])
        self.assertIn("cid:nepal-telecom-logo-mobile", mail.outbox[0].alternatives[0][0])
        self.assertIn(req.request_number, mail.outbox[0].subject)
        self.assertIn("Submit", mail.outbox[0].subject)
        self.assertIn("SUBMITTED", mail.outbox[0].body)

    def test_submit_notifies_section_head_not_actor(self):
        req = make_request(self.staff)
        perform(req, self.staff, "submit")
        self.assertEqual(Notification.objects.filter(recipient=self.it_head, request=req).count(), 1)
        self.assertFalse(Notification.objects.filter(recipient=self.staff).exists())
        self.assertFalse(Notification.objects.filter(recipient=self.rs_head).exists())

    def test_workflow_events_notify_the_right_people(self):
        req = make_request(self.staff)
        perform(req, self.staff, "submit")
        perform(req, self.it_head, "verify")
        self.assertTrue(Notification.objects.filter(recipient=self.darta, request=req).exists())
        self.assertTrue(Notification.objects.filter(recipient=self.staff, title="Request verified").exists())
        perform(req, self.darta, "register")
        perform(req, self.darta, "forward", {"to_department": self.dept("KP").pk})
        self.assertTrue(Notification.objects.filter(recipient=self.kp, title="Request forwarded to you").exists())
        perform(req, self.kp, "approve")
        self.assertTrue(Notification.objects.filter(recipient=self.chalani, request=req).exists())
        self.assertTrue(Notification.objects.filter(recipient=self.staff, title="Request approved").exists())

    def test_reject_and_return_notify_requester_with_reason(self):
        req = make_request(self.staff)
        perform(req, self.staff, "submit")
        perform(req, self.it_head, "return", {"remarks": "Add the quotation"})
        n = Notification.objects.get(recipient=self.staff, title="Request returned")
        self.assertIn("Add the quotation", n.message)
        self.assertEqual(n.level, "warn")
        self.assertFalse(n.is_read)

    def test_inactive_recipients_are_skipped(self):
        self.staff.is_active = False
        notify([self.staff, None, self.it_head, self.it_head], None, "Hello")
        self.assertEqual(Notification.objects.count(), 1)


class NotificationViewTests(DartaTestCase):
    def setUp(self):
        self.req = make_request(self.staff)
        perform(self.req, self.staff, "submit")
        self.note = Notification.objects.get(recipient=self.it_head)

    @override_settings(
        EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
        WORKFLOW_NOTIFICATION_EMAIL="poksamir@gmail.com",
        DEFAULT_FROM_EMAIL="DartaLink <noreply@example.test>",
    )
    def test_admin_can_send_direct_message_to_employee(self):
        self.login(self.admin)
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(reverse("notifications:send"), {
                "subject": "System issue",
                "department": self.dept("IT").pk,
                "recipient_mode": "individual",
                "recipients": [self.staff.pk],
                "body": "Please review the printer issue.",
            })
        self.assertRedirects(response, reverse("notifications:list"))
        message = DirectMessage.objects.get(recipient=self.staff)
        self.assertEqual(message.sender, self.admin)
        self.assertEqual(Notification.objects.get(recipient=self.staff).title, "System issue")
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["poksamir@gmail.com"])

    @override_settings(
        EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
        WORKFLOW_NOTIFICATION_EMAIL="poksamir@gmail.com",
        USE_EMPLOYEE_EMAILS=True,
        DEFAULT_FROM_EMAIL="DartaLink <noreply@example.test>",
    )
    def test_direct_message_uses_employee_email_when_enabled(self):
        self.login(self.admin)
        with self.captureOnCommitCallbacks(execute=True):
            self.client.post(reverse("notifications:send"), {
                "subject": "Employee delivery",
                "department": self.dept("IT").pk,
                "recipient_mode": "individual",
                "recipients": [self.staff.pk],
                "body": "Delivered to the employee address.",
            })
        self.assertEqual(mail.outbox[0].to, [self.staff.email])

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def test_employee_can_open_direct_message_notification(self):
        self.login(self.admin)
        with self.captureOnCommitCallbacks(execute=True):
            self.client.post(reverse("notifications:send"), {
                "subject": "System issue",
                "department": self.dept("IT").pk,
                "recipient_mode": "individual",
                "recipients": [self.staff.pk],
                "body": "Please review the printer issue.",
            })

        notification = Notification.objects.get(recipient=self.staff, title="System issue")
        self.login(self.staff)
        response = self.client.get(reverse("notifications:open", args=[notification.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "System issue")
        self.assertContains(response, "Please review the printer issue.")
        notification.refresh_from_db()
        self.assertTrue(notification.is_read)

    def test_employee_can_open_legacy_direct_message_notification(self):
        message = DirectMessage.objects.create(
            sender=self.admin,
            recipient=self.staff,
            subject="Legacy subject",
            body="Legacy message body.",
        )
        notification = Notification.objects.create(
            recipient=self.staff,
            title=message.subject,
            message=f"From {self.admin.display_name}: {message.body}",
        )
        self.login(self.staff)
        response = self.client.get(reverse("notifications:open", args=[notification.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Legacy subject")
        self.assertContains(response, "Legacy message body.")
        notification.refresh_from_db()
        self.assertEqual(notification.direct_message_id, message.pk)

    def test_non_admin_cannot_send_direct_message(self):
        self.login(self.staff)
        self.assertEqual(self.client.get(reverse("notifications:send")).status_code, 403)

    def test_send_message_only_highlights_send_message_sidebar_item(self):
        self.login(self.admin)
        response = self.client.get(reverse("notifications:send"))
        active_links = [
            item
            for group in response.context["nav_groups"]
            for item in group["items"]
            if item["active"]
        ]
        self.assertEqual([item["label"] for item in active_links], ["Send message"])

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def test_admin_can_send_to_all_employees_in_department(self):
        self.login(self.admin)
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(reverse("notifications:send"), {
                "subject": "IT maintenance",
                "department": self.dept("IT").pk,
                "recipient_mode": "all",
                "body": "Please be available for maintenance.",
            })
        self.assertRedirects(response, reverse("notifications:list"))
        self.assertEqual(DirectMessage.objects.filter(subject="IT maintenance").count(), 2)

    def test_individual_recipients_must_match_department(self):
        self.login(self.admin)
        response = self.client.post(reverse("notifications:send"), {
            "subject": "Check",
            "department": self.dept("IT").pk,
            "recipient_mode": "individual",
            "recipients": [self.staff.pk, self.other.pk],
            "body": "Please check.",
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Employees must belong to the selected department.")
        self.assertFalse(DirectMessage.objects.filter(subject="Check").exists())

    def test_bell_shows_unread_count(self):
        r = self.login(self.it_head).get(reverse("dashboard:home"))
        self.assertEqual(r.context["unread_count"], 1)
        self.assertContains(r, 'id="bell-badge"')
        self.assertContains(r, "notif-item unread")

    def test_open_marks_read_and_redirects_to_request(self):
        self.login(self.it_head)
        r = self.client.get(reverse("notifications:open", args=[self.note.pk]))
        self.assertRedirects(r, self.req.get_absolute_url())
        self.note.refresh_from_db()
        self.assertTrue(self.note.is_read)
        self.assertEqual(self.client.get(reverse("dashboard:home")).context["unread_count"], 0)

    def test_cannot_touch_someone_elses_notification(self):
        self.login(self.staff)
        self.assertEqual(self.client.get(reverse("notifications:open", args=[self.note.pk])).status_code, 404)
        self.client.post(reverse("notifications:mark_read", args=[self.note.pk]))
        self.note.refresh_from_db()
        self.assertFalse(self.note.is_read)

    def test_mark_all_read_and_unread_count_json(self):
        self.login(self.it_head)
        self.assertEqual(self.client.get(reverse("notifications:unread_count")).json(), {"unread": 1})
        r = self.client.post(reverse("notifications:mark_all_read"), HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        self.assertEqual(r.json(), {"unread": 0})
        self.assertEqual(self.client.get(reverse("notifications:unread_count")).json(), {"unread": 0})

    def test_list_and_unread_filter(self):
        self.login(self.it_head)
        self.assertEqual(len(self.client.get(reverse("notifications:list")).context["page"]), 1)
        Notification.objects.filter(pk=self.note.pk).update(is_read=True)
        self.assertEqual(len(self.client.get(reverse("notifications:list"), {"filter": "unread"}).context["page"]), 0)

    def test_notifications_page_does_not_show_send_message_button(self):
        self.login(self.admin)
        response = self.client.get(reverse("notifications:list"))
        self.assertNotContains(
            response,
            f'class="btn btn-primary" href="{reverse("notifications:send")}"',
        )

    def test_open_falls_back_when_request_no_longer_visible(self):
        n = Notification.objects.create(recipient=self.other, request=self.req, title="stale")
        self.login(self.other)
        r = self.client.get(reverse("notifications:open", args=[n.pk]))
        self.assertRedirects(r, reverse("notifications:list"))
