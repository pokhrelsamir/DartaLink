from django.test import RequestFactory
from django.urls import reverse

from core.testutils import DartaTestCase, make_request
from core.views import error_500
from workflow.services import perform


class DashboardTests(DartaTestCase):
    def test_every_role_gets_a_dashboard_with_role_specific_cards(self):
        expectations = [
            (self.admin, "Active users"), (self.staff, "My requests"), (self.it_head, "Awaiting verification"),
            (self.kp, "In your inbox"), (self.darta, "To register"), (self.chalani, "To process"),
        ]
        for user, label in expectations:
            r = self.login(user).get(reverse("dashboard:home"))
            self.assertEqual(r.status_code, 200, user.username)
            self.assertContains(r, label)
            self.assertContains(r, user.staff_id)

    def test_counts_reflect_workflow_state(self):
        req = make_request(self.staff)
        perform(req, self.staff, "submit")
        r = self.login(self.it_head).get(reverse("dashboard:home"))
        cards = {c["label"]: c["value"] for c in r.context["cards"]}
        self.assertEqual(cards["Awaiting verification"], 1)
        perform(req, self.it_head, "verify")
        cards = {c["label"]: c["value"] for c in self.login(self.darta).get(reverse("dashboard:home")).context["cards"]}
        self.assertEqual(cards["To register"], 1)
        queue = self.client.get(reverse("dashboard:home")).context["queue"]
        self.assertEqual([q.pk for q in queue], [req.pk])

    def test_sidebar_navigation_is_role_based(self):
        html = self.login(self.staff).get(reverse("dashboard:home")).content.decode()
        self.assertNotIn("Audit log", html)
        self.assertNotIn("/accounts/users/", html)
        self.assertIn("New request", html)
        html = self.login(self.admin).get(reverse("dashboard:home")).content.decode()
        self.assertIn("Audit log", html)
        self.assertIn("/accounts/users/", html)
        self.assertNotIn("New request", html)

    def test_branding_and_layout(self):
        html = self.login(self.staff).get(reverse("dashboard:home")).content.decode()
        self.assertIn("nt-logo.png", html)
        self.assertIn('class="skip-link"', html)
        self.assertIn('aria-label="Breadcrumb"', html)

    def test_audit_log_lists_actions_for_sysadmin(self):
        req = make_request(self.staff)
        perform(req, self.staff, "submit")
        r = self.login(self.admin).get(reverse("workflow:audit"), {"q": req.request_number})
        self.assertEqual(r.context["page"].paginator.count, 1)


class ErrorPageTests(DartaTestCase):
    def test_custom_404_and_403_pages(self):
        r = self.client.get("/definitely/not/here/")
        self.assertEqual(r.status_code, 404)
        self.assertContains(r, "Page not found", status_code=404)
        self.login(self.staff)
        r = self.client.get(reverse("accounts:user_list"))
        self.assertEqual(r.status_code, 403)
        self.assertContains(r, "Access denied", status_code=403)

    def test_500_page_renders(self):
        r = error_500(RequestFactory().get("/"))
        self.assertEqual(r.status_code, 500)
        self.assertIn(b"Something went wrong", r.content)
