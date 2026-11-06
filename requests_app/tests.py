import re

from django.contrib.messages import get_messages
from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, override_settings
from django.urls import reverse
from django.utils import timezone

from core.testutils import DartaTestCase, make_request
from workflow.models import Annotation, WorkflowLog
from workflow.services import Invalid, NotAllowed, available_actions, perform

from .models import AdministrativeRequest, Status


def run_to_registered(test, req):
    perform(req, test.staff, "submit")
    perform(req, test.it_head, "verify")
    perform(req, test.darta, "register")


class NumberingTests(DartaTestCase):
    def test_request_numbers_are_unique_and_formatted(self):
        a, b = make_request(self.staff), make_request(self.staff)
        self.assertRegex(a.request_number, r"^DL-REQ-\d{4}-\d{5}$")
        self.assertNotEqual(a.request_number, b.request_number)

    def test_darta_and_chalani_numbers_increment(self):
        r1, r2 = make_request(self.staff), make_request(self.other)
        run_to_registered(self, r1)
        perform(r2, self.other, "submit")
        perform(r2, self.rs_head, "verify")
        perform(r2, self.darta, "register")
        r1.refresh_from_db(); r2.refresh_from_db()
        self.assertRegex(r1.darta_number, r"^DARTA-\d{4}/\d{2}-0001$")
        self.assertTrue(r2.darta_number.endswith("-0002"))
        for r in (r1, r2):
            perform(r, self.darta, "forward", {"to_department": self.dept("KP").pk})
            perform(r, self.kp, "approve")
            perform(r, self.chalani, "dispatch", {"dispatched_to": "Head Office"})
        r1.refresh_from_db(); r2.refresh_from_db()
        self.assertRegex(r1.chalani_number, r"^CHALANI-\d{4}/\d{2}-0001$")
        self.assertTrue(r2.chalani_number.endswith("-0002"))


class DartaIntakeTests(DartaTestCase):
    def test_customer_name_and_contact_are_validated(self):
        self.login(self.darta)
        form_data = {
            "title": "Customer service request",
            "category": "OTHER",
            "priority": "HIGH",
            "description": "Customer supplied the request.",
            "customer_name": "Ram123",
            "customer_contact": "98000000001",
            "department": self.dept("IT").pk,
        }
        response = self.client.post(reverse("requests:create"), form_data)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Customer name must contain alphabetic characters and spaces only.")
        self.assertContains(response, "Customer contact must contain up to 10 digits only.")
        self.assertFalse(AdministrativeRequest.objects.filter(title="Customer service request").exists())

    def test_darta_can_capture_customer_and_route_to_receiving_branch(self):
        response = self.login(self.darta).post(reverse("requests:create"), {
            "title": "Customer service request",
            "category": "OTHER",
            "priority": "HIGH",
            "description": "Customer supplied the request and supporting documents at the counter.",
            "customer_name": "Ram Bahadur",
            "customer_contact": "9800000000",
            "department": self.dept("IT").pk,
            "submit_now": "1",
        })
        self.assertEqual(response.status_code, 302)
        req = AdministrativeRequest.objects.get(title="Customer service request")
        self.assertEqual((req.customer_name, req.intake_by, req.department), ("Ram Bahadur", self.darta, self.dept("IT")))
        self.assertEqual((req.status, req.current_department), (Status.SUBMITTED, self.dept("IT")))
        perform(req, self.staff, "prepare_review")
        req.refresh_from_db()
        self.assertEqual(req.status, Status.BRANCH_REVIEW)
        perform(req, self.it_head, "verify")
        req.refresh_from_db()
        self.assertEqual((req.status, req.current_department), (Status.VERIFIED, self.dept("DT")))
        self.assertEqual(req.branch_verified_by, self.it_head)
        self.assertIsNotNone(req.branch_verified_at)
        perform(req, self.darta, "register")
        req.refresh_from_db()
        self.assertEqual(req.status, Status.REGISTERED)


class WorkflowHappyPathTests(DartaTestCase):
    def test_full_lifecycle(self):
        req = make_request(self.staff)
        self.assertEqual(req.status, Status.DRAFT)
        perform(req, self.staff, "submit")
        req.refresh_from_db()
        self.assertEqual((req.status, req.current_department), (Status.SUBMITTED, self.dept("IT")))
        perform(req, self.it_head, "verify")
        req.refresh_from_db()
        self.assertEqual((req.status, req.current_department), (Status.VERIFIED, self.dept("DT")))
        perform(req, self.darta, "register")
        req.refresh_from_db()
        self.assertEqual(req.status, Status.REGISTERED)
        self.assertTrue(req.darta_number and req.darta_date and req.registered_by == self.darta)
        perform(req, self.darta, "forward", {"to_department": self.dept("PP").pk, "remarks": "Please review"})
        req.refresh_from_db()
        self.assertEqual((req.status, req.current_department), (Status.FORWARDED, self.dept("PP")))
        perform(req, self.pp, "recommend", {"remarks": "Technically sound"})
        perform(req, self.pp, "tippani", {"remarks": "File note"})
        req.refresh_from_db()
        self.assertEqual(req.status, Status.UNDER_REVIEW)
        perform(req, self.pp, "forward", {"to_department": self.dept("KP").pk})
        perform(req, self.kp, "tok_aadesh", {"remarks": "Proceed"})
        perform(req, self.kp, "approve", {"remarks": "Approved"})
        req.refresh_from_db()
        self.assertEqual((req.status, req.current_department, req.approved_by), (Status.APPROVED, self.dept("CH"), self.kp))
        perform(req, self.chalani, "process")
        perform(req, self.chalani, "dispatch", {"dispatched_to": "Procurement Unit"})
        req.refresh_from_db()
        self.assertEqual(req.status, Status.DISPATCHED)
        self.assertTrue(req.chalani_number and req.dispatched_to == "Procurement Unit")
        perform(req, self.chalani, "complete")
        req.refresh_from_db()
        self.assertEqual(req.status, Status.COMPLETED)
        self.assertIsNotNone(req.completed_at)
        self.assertEqual(Annotation.objects.filter(request=req).count(), 3)
        actions = list(req.logs.values_list("action", flat=True))
        self.assertEqual(actions[0], "submit")
        self.assertEqual(actions[-1], "complete")
        self.assertEqual(len(actions), 12)


class ApprovalConfirmationTests(DartaTestCase):
    def test_approved_request_confirmation_is_available_to_chalani(self):
        req = make_request(self.staff, status=Status.APPROVED, approved_by=self.kp,
                           approved_at=timezone.now(), current_department=self.dept("CH"))
        self.login(self.chalani)
        response = self.client.get(reverse("requests:approval_confirmation", args=[req.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Approved · awaiting dispatch")
        self.assertContains(response, "Print confirmation")

    def test_completed_confirmation_shows_current_stage(self):
        req = make_request(self.staff, status=Status.COMPLETED, approved_by=self.kp,
                           approved_at=timezone.now(), current_department=self.dept("CH"))
        self.login(self.chalani)
        response = self.client.get(reverse("requests:approval_confirmation", args=[req.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Completed")

    def test_confirmation_is_not_available_before_approval(self):
        req = make_request(self.staff, status=Status.FORWARDED, current_department=self.dept("PP"))
        self.login(self.chalani)
        response = self.client.get(reverse("requests:approval_confirmation", args=[req.pk]))
        self.assertEqual(response.status_code, 404)

    def test_pramukh_request_skips_section_verification(self):
        req = make_request(self.it_head)
        perform(req, self.it_head, "submit")
        req.refresh_from_db()
        self.assertEqual(req.status, Status.VERIFIED)

    def test_return_then_resubmit_keeps_darta_number(self):
        req = make_request(self.staff)
        run_to_registered(self, req)
        req.refresh_from_db()
        number = req.darta_number
        perform(req, self.darta, "forward", {"to_department": self.dept("LP").pk})
        perform(req, self.lp, "return", {"remarks": "Add quotation"})
        req.refresh_from_db()
        self.assertEqual(req.status, Status.RETURNED)
        self.assertTrue(req.can_edit(self.staff))
        perform(req, self.staff, "submit")
        perform(req, self.it_head, "verify")
        perform(req, self.darta, "register")
        req.refresh_from_db()
        self.assertEqual(req.darta_number, number)

    def test_reject_and_cancel(self):
        req = make_request(self.staff)
        run_to_registered(self, req)
        perform(req, self.darta, "forward", {"to_department": self.dept("KP").pk})
        perform(req, self.kp, "reject", {"remarks": "No budget"})
        req.refresh_from_db()
        self.assertEqual((req.status, req.decision_remarks), (Status.REJECTED, "No budget"))
        draft = make_request(self.staff)
        perform(draft, self.staff, "cancel")
        draft.refresh_from_db()
        self.assertEqual(draft.status, Status.CANCELLED)


class WorkflowPermissionTests(DartaTestCase):
    def test_staff_cannot_verify_or_approve(self):
        req = make_request(self.staff)
        perform(req, self.staff, "submit")
        with self.assertRaises(NotAllowed):
            perform(req, self.staff, "verify")
        with self.assertRaises(NotAllowed):
            perform(req, self.kp, "approve")

    def test_other_sections_pramukh_cannot_verify(self):
        req = make_request(self.staff)
        perform(req, self.staff, "submit")
        with self.assertRaises(NotAllowed):
            perform(req, self.rs_head, "verify")

    def test_actions_are_blocked_in_the_wrong_stage(self):
        req = make_request(self.staff)
        with self.assertRaises(NotAllowed):
            perform(req, self.darta, "register")
        perform(req, self.staff, "submit")
        with self.assertRaises(NotAllowed):
            perform(req, self.darta, "register")      # not verified yet
        with self.assertRaises(NotAllowed):
            perform(req, self.chalani, "dispatch")

    def test_only_karyalaya_pramukh_decides_and_issues_tok_aadesh(self):
        req = make_request(self.staff)
        run_to_registered(self, req)
        perform(req, self.darta, "forward", {"to_department": self.dept("PP").pk})
        for action in ("approve", "reject", "tok_aadesh"):
            with self.assertRaises(NotAllowed):
                perform(req, self.pp, action, {"remarks": "x"})
        with self.assertRaises(NotAllowed):      # KP does not hold it yet
            perform(req, self.kp, "approve")

    def test_only_current_authority_can_annotate(self):
        req = make_request(self.staff)
        run_to_registered(self, req)
        perform(req, self.darta, "forward", {"to_department": self.dept("PP").pk})
        with self.assertRaises(NotAllowed):
            perform(req, self.lp, "recommend", {"remarks": "hi"})
        with self.assertRaises(NotAllowed):
            perform(req, self.darta, "recommend", {"remarks": "hi"})

    def test_remarks_and_forward_target_validation(self):
        req = make_request(self.staff)
        run_to_registered(self, req)
        with self.assertRaises(Invalid):
            perform(req, self.darta, "forward", {})
        with self.assertRaises(Invalid):
            perform(req, self.darta, "forward", {"to_department": self.dept("CH").pk})  # not an authority
        perform(req, self.darta, "forward", {"to_department": self.dept("KP").pk})
        with self.assertRaises(Invalid):
            perform(req, self.kp, "reject", {"remarks": "  "})
        with self.assertRaises(Invalid):
            perform(req, self.kp, "return", {})

    def test_dispatch_requires_recipient(self):
        req = make_request(self.staff)
        run_to_registered(self, req)
        perform(req, self.darta, "forward", {"to_department": self.dept("KP").pk})
        perform(req, self.kp, "approve")
        with self.assertRaises(Invalid):
            perform(req, self.chalani, "dispatch", {})

    def test_inactive_user_cannot_act(self):
        req = make_request(self.staff)
        self.staff.is_active = False
        with self.assertRaises(NotAllowed):
            perform(req, self.staff, "submit")

    def test_available_actions_reflect_role_and_stage(self):
        req = make_request(self.staff)
        self.assertEqual({a["key"] for a in available_actions(req, self.staff)}, {"submit", "cancel"})
        self.assertEqual(available_actions(req, self.darta), [])
        perform(req, self.staff, "submit")
        self.assertEqual({a["key"] for a in available_actions(req, self.it_head)}, {"verify", "reject", "return"})


class VisibilityTests(DartaTestCase):
    def test_section_isolation(self):
        req = make_request(self.staff)
        perform(req, self.staff, "submit")
        url = reverse("requests:detail", args=[req.pk])
        self.assertEqual(self.login(self.staff).get(url).status_code, 200)
        self.assertEqual(self.login(self.it_head).get(url).status_code, 200)
        self.assertEqual(self.login(self.admin).get(url).status_code, 200)
        for outsider in (self.other, self.rs_head, self.kp, self.pp, self.darta, self.chalani):
            self.assertEqual(self.login(outsider).get(url).status_code, 404, outsider.username)

    def test_drafts_are_private_to_the_requester(self):
        req = make_request(self.staff)
        url = reverse("requests:detail", args=[req.pk])
        self.assertEqual(self.login(self.it_head).get(url).status_code, 404)
        self.assertEqual(self.login(self.staff).get(url).status_code, 200)

    def test_registry_and_authority_visibility_follow_the_workflow(self):
        req = make_request(self.staff)
        run_to_registered(self, req)
        url = reverse("requests:detail", args=[req.pk])
        self.assertEqual(self.login(self.darta).get(url).status_code, 200)
        self.assertEqual(self.login(self.kp).get(url).status_code, 200)       # head of office sees registered files
        self.assertEqual(self.login(self.chalani).get(url).status_code, 404)  # not approved yet
        self.assertEqual(self.login(self.pp).get(url).status_code, 404)       # not forwarded yet
        perform(req, self.darta, "forward", {"to_department": self.dept("PP").pk})
        self.assertEqual(self.login(self.pp).get(url).status_code, 200)
        self.assertEqual(self.login(self.lp).get(url).status_code, 404)

    def test_list_only_contains_visible_requests(self):
        mine, theirs = make_request(self.staff, title="IT secret"), make_request(self.other, title="RS secret")
        self.login(self.staff)
        r = self.client.get(reverse("requests:list"))
        titles = [x.title for x in r.context["page"]]
        self.assertIn("IT secret", titles)
        self.assertNotIn("RS secret", titles)


class RequestViewTests(DartaTestCase):
    def payload(self, **extra):
        data = {"title": "New monitor", "category": "PROCUREMENT", "priority": "HIGH",
                "description": "Need a second monitor.", "requested_amount": "25000", "required_by": ""}
        data.update(extra)
        return data

    def test_create_draft_and_submit_now(self):
        self.login(self.staff)
        r = self.client.post(reverse("requests:create"), self.payload(save="1"))
        req = AdministrativeRequest.objects.get(title="New monitor")
        self.assertRedirects(r, req.get_absolute_url())
        self.assertEqual((req.status, req.requester, req.department), (Status.DRAFT, self.staff, self.dept("IT")))
        r = self.client.post(reverse("requests:create"), self.payload(title="Second", submit_now="1"))
        self.assertEqual(AdministrativeRequest.objects.get(title="Second").status, Status.SUBMITTED)

    @override_settings(
        EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
        WORKFLOW_NOTIFICATION_EMAIL="poksamir6@gmail.com",
        WORKFLOW_CC_EMAILS=["poksamir6@gmail.com"],
        WORKFLOW_ROLE_EMAILS={"IT_PRAMUKH": "it-chief@example.test"},
        DEFAULT_FROM_EMAIL="DartaLink <noreply@example.test>",
    )
    def test_creating_request_sends_workflow_email(self):
        self.login(self.staff)
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(reverse("requests:create"), self.payload(save="1"))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["it-chief@example.test"])
        self.assertEqual(mail.outbox[0].cc, ["poksamir6@gmail.com"])
        self.assertIn("Create", mail.outbox[0].subject)

    def test_sysadmin_cannot_create_requests(self):
        self.login(self.admin)
        self.assertEqual(self.client.get(reverse("requests:create")).status_code, 403)

    def test_invalid_form_and_bad_attachment_create_nothing(self):
        self.login(self.staff)
        r = self.client.post(reverse("requests:create"), self.payload(title=""))
        self.assertEqual(r.status_code, 200)
        bad = SimpleUploadedFile("virus.exe", b"MZ....", content_type="application/octet-stream")
        r = self.client.post(reverse("requests:create"), {**self.payload(), "files": bad})
        self.assertEqual(r.status_code, 200)
        self.assertFalse(AdministrativeRequest.objects.exists())

    def test_edit_allowed_only_while_draft_or_returned(self):
        req = make_request(self.staff)
        url = reverse("requests:edit", args=[req.pk])
        self.login(self.staff)
        r = self.client.post(url, self.payload(title="Edited", save="1"))
        self.assertRedirects(r, req.get_absolute_url())
        req.refresh_from_db()
        self.assertEqual(req.title, "Edited")
        perform(req, self.staff, "submit")
        self.assertEqual(self.client.get(url).status_code, 403)
        self.assertEqual(self.client.post(url, self.payload(title="Hack")).status_code, 403)
        req.refresh_from_db()
        self.assertEqual(req.title, "Edited")

    def test_action_endpoint_enforces_roles_and_reports_errors(self):
        req = make_request(self.staff)
        perform(req, self.staff, "submit")
        url = reverse("requests:action", args=[req.pk, "verify"])
        self.login(self.staff)
        r = self.client.post(url, follow=True)
        req.refresh_from_db()
        self.assertEqual(req.status, Status.SUBMITTED)
        self.assertTrue(any(m.level_tag == "error" for m in get_messages(r.wsgi_request)))
        self.assertEqual(self.client.get(url).status_code, 405)    # POST only
        self.login(self.it_head)
        self.client.post(url)
        req.refresh_from_db()
        self.assertEqual(req.status, Status.VERIFIED)

    def test_action_endpoint_is_hidden_from_outsiders_and_needs_csrf(self):
        req = make_request(self.staff)
        perform(req, self.staff, "submit")
        url = reverse("requests:action", args=[req.pk, "verify"])
        self.assertEqual(self.login(self.rs_head).post(url).status_code, 404)
        c = Client(enforce_csrf_checks=True)
        c.force_login(self.it_head)
        self.assertEqual(c.post(url).status_code, 403)

    def test_detail_renders_modals_for_available_actions_only(self):
        req = make_request(self.staff)
        perform(req, self.staff, "submit")
        html = self.login(self.it_head).get(reverse("requests:detail", args=[req.pk])).content.decode()
        self.assertIn('id="modal-verify"', html)
        self.assertIn('id="modal-return"', html)
        self.assertNotIn('id="modal-approve"', html)
        html = self.login(self.staff).get(reverse("requests:detail", args=[req.pk])).content.decode()
        self.assertNotIn('id="modal-verify"', html)

    def test_timeline_is_chronological(self):
        req = make_request(self.staff)
        run_to_registered(self, req)
        actions = [l.action for l in req.logs.all()]
        self.assertEqual(actions, ["submit", "verify", "register"])
        html = self.login(self.staff).get(req.get_absolute_url()).content.decode()
        self.assertLess(html.index("Submitted"), html.index("Registered in Darta"))


class SearchFilterTests(DartaTestCase):
    def setUp(self):
        self.a = make_request(self.staff, title="Router replacement", category="PROCUREMENT", priority="URGENT")
        self.b = make_request(self.staff, title="Leave application", category="LEAVE")
        perform(self.b, self.staff, "submit")
        self.login(self.staff)

    def results(self, **params):
        r = self.client.get(reverse("requests:list"), {"scope": "mine", **params})
        return {x.pk for x in r.context["page"]}

    def test_filters(self):
        self.assertEqual(self.results(q="router"), {self.a.pk})
        self.assertEqual(self.results(q=self.b.request_number), {self.b.pk})
        self.assertEqual(self.results(status="SUBMITTED"), {self.b.pk})
        self.assertEqual(self.results(category="PROCUREMENT"), {self.a.pk})
        self.assertEqual(self.results(priority="URGENT"), {self.a.pk})
        self.assertEqual(self.results(department=self.dept("IT").pk), {self.a.pk, self.b.pk})
        self.assertEqual(self.results(department=self.dept("RS").pk), set())
        self.assertEqual(self.results(date_from="2999-01-01"), set())
        self.assertEqual(self.results(status="NOT-A-STATUS"), {self.a.pk, self.b.pk})  # ignored safely

    def test_scope_action_shows_drafts_waiting_on_me(self):
        self.assertEqual(self.results(scope="action"), {self.a.pk})

    def test_pagination(self):
        for i in range(12):
            make_request(self.staff, title=f"Bulk {i}")
        r = self.client.get(reverse("requests:list"), {"scope": "mine"})
        self.assertEqual(len(r.context["page"]), 10)
        self.assertEqual(r.context["page"].paginator.num_pages, 2)
        r = self.client.get(reverse("requests:list"), {"scope": "mine", "page": 2})
        self.assertEqual(len(r.context["page"]), 4)
        self.assertEqual(self.client.get(reverse("requests:list"), {"page": "junk"}).status_code, 200)


class RequestReportTests(DartaTestCase):
    def setUp(self):
        self.match = make_request(self.staff, title="Reportable router", category="PROCUREMENT")
        self.other = make_request(self.staff, title="Unmatched leave", category="LEAVE")

    def test_report_and_pdf_are_admin_only_and_use_filters(self):
        params = {"q": "router", "category": "PROCUREMENT", "status": "DRAFT"}
        self.login(self.admin)
        report = self.client.get(reverse("requests:report"), params)
        self.assertEqual(report.status_code, 200)
        self.assertContains(report, self.match.request_number)
        self.assertNotContains(report, self.other.request_number)
        self.assertContains(report, "Export PDF")

        pdf = self.client.get(reverse("requests:report_pdf"), params)
        self.assertEqual(pdf.status_code, 200)
        self.assertEqual(pdf["Content-Type"], "application/pdf")
        self.assertTrue(pdf.content.startswith(b"%PDF-"))
        self.assertGreater(len(pdf.content), 1000)

    def test_report_endpoints_reject_non_admin_users(self):
        self.login(self.staff)
        self.assertEqual(self.client.get(reverse("requests:report")).status_code, 403)
        self.assertEqual(self.client.get(reverse("requests:report_pdf")).status_code, 403)
        response = self.client.get(reverse("requests:list"))
        self.assertNotContains(response, "View / print report")


class DartaChalaniProcessTests(DartaTestCase):
    def test_darta_queue_and_registration_via_http(self):
        req = make_request(self.staff)
        perform(req, self.staff, "submit")
        perform(req, self.it_head, "verify")
        self.login(self.darta)
        r = self.client.get(reverse("requests:list"), {"scope": "action"})
        self.assertIn(req.pk, {x.pk for x in r.context["page"]})
        self.client.post(reverse("requests:action", args=[req.pk, "register"]), {"remarks": "ok"})
        req.refresh_from_db()
        self.assertEqual(req.status, Status.REGISTERED)
        self.assertTrue(req.darta_number)

    def test_chalani_only_sees_approved_onwards_and_can_dispatch(self):
        req = make_request(self.staff)
        run_to_registered(self, req)
        perform(req, self.darta, "forward", {"to_department": self.dept("KP").pk})
        self.login(self.chalani)
        self.assertEqual(self.client.get(req.get_absolute_url()).status_code, 404)
        perform(req, self.kp, "approve")
        self.assertEqual(self.client.get(req.get_absolute_url()).status_code, 200)
        self.client.post(reverse("requests:action", args=[req.pk, "dispatch"]), {"dispatched_to": "Finance"})
        req.refresh_from_db()
        self.assertEqual(req.status, Status.DISPATCHED)
        self.assertEqual(req.dispatched_by, self.chalani)
