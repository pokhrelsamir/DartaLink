from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient

from core.testutils import PW, DartaTestCase, make_request
from notifications.models import Notification
from requests_app.models import AdministrativeRequest, Status
from workflow.services import perform


class ApiBase(DartaTestCase):
    def setUp(self):
        self.api = APIClient()

    def as_user(self, user):
        self.api.force_login(user)
        return self.api


class ApiAuthTests(ApiBase):
    def test_requires_authentication(self):
        for path in ("/api/requests/", "/api/departments/", "/api/users/", "/api/notifications/", "/api/documents/"):
            self.assertIn(self.api.get(path).status_code, (401, 403), path)

    def test_schema_and_swagger_ui_are_served(self):
        r = self.api.get("/api/schema/")
        self.assertEqual(r.status_code, 200)
        self.assertIn(b"openapi", r.content)
        self.assertIn(b"DartaLink API", r.content)
        self.assertEqual(self.api.get("/api/docs/").status_code, 200)


class ApiDirectoryTests(ApiBase):
    def test_departments_read_for_all_write_for_admin_only(self):
        self.as_user(self.staff)
        r = self.api.get("/api/departments/")
        self.assertEqual(r.status_code, 200)
        self.assertGreaterEqual(r.data["count"], 8)
        self.assertEqual(self.api.post("/api/departments/", {"name": "X", "code": "XX"}, format="json").status_code, 403)
        self.as_user(self.admin)
        r = self.api.post("/api/departments/", {"name": "Legal Sakha", "code": "lg", "is_authority": True}, format="json")
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.data["code"], "LG")

    def test_users_me_and_directory_does_not_leak_email(self):
        self.as_user(self.staff)
        me = self.api.get("/api/users/me/").data
        self.assertEqual((me["staff_id"], me["role"]), ("NTC-IT-002", "STAFF"))
        row = self.api.get("/api/users/").data["results"][0]
        self.assertNotIn("email", row)
        self.assertEqual(self.api.post("/api/users/", {}, format="json").status_code, 403)

    def test_admin_creates_user_with_generated_staff_id(self):
        self.as_user(self.admin)
        r = self.api.post("/api/users/", {
            "username": "apiuser", "first_name": "Api", "email": "a@x.test", "role": "STAFF",
            "department": self.dept("BS").pk, "password": PW, "profile": {"designation": "Officer"}}, format="json")
        self.assertEqual(r.status_code, 201, r.data)
        self.assertEqual(r.data["staff_id"], "NTC-BS-001")
        self.assertNotIn("password", r.data)
        bad = self.api.post("/api/users/", {"username": "bad", "role": "DARTA_STAFF",
                                            "department": self.dept("IT").pk, "password": PW}, format="json")
        self.assertEqual(bad.status_code, 400)


class ApiRequestTests(ApiBase):
    def body(self, **kw):
        data = {"title": "API request", "description": "Created over REST", "category": "IT_SUPPORT", "priority": "HIGH"}
        data.update(kw)
        return data

    def test_create_update_and_lock_after_submit(self):
        self.as_user(self.staff)
        r = self.api.post("/api/requests/", self.body(), format="json")
        self.assertEqual(r.status_code, 201, r.data)
        pk = r.data["id"]
        req = AdministrativeRequest.objects.get(pk=pk)
        self.assertEqual((req.status, req.requester, req.department), (Status.DRAFT, self.staff, self.dept("IT")))
        self.assertEqual(self.api.patch(f"/api/requests/{pk}/", {"title": "Renamed"}, format="json").status_code, 200)
        self.api.post(f"/api/requests/{pk}/actions/", {"action": "submit"}, format="json")
        self.assertEqual(self.api.patch(f"/api/requests/{pk}/", {"title": "Hack"}, format="json").status_code, 403)
        req.refresh_from_db()
        self.assertEqual((req.title, req.status), ("Renamed", Status.SUBMITTED))

    def test_client_cannot_set_system_fields(self):
        self.as_user(self.staff)
        r = self.api.post("/api/requests/", self.body(status="APPROVED", darta_number="HACK", requester=self.kp.pk), format="json")
        self.assertEqual(r.status_code, 201)
        req = AdministrativeRequest.objects.get(pk=r.data["id"])
        self.assertEqual((req.status, req.darta_number, req.requester), (Status.DRAFT, "", self.staff))

    def test_workflow_actions_over_api(self):
        req = make_request(self.staff)
        self.as_user(self.staff)
        self.assertEqual(self.api.post(f"/api/requests/{req.pk}/actions/", {"action": "submit"}, format="json").status_code, 200)
        r = self.api.post(f"/api/requests/{req.pk}/actions/", {"action": "verify"}, format="json")
        self.assertEqual(r.status_code, 403)
        self.as_user(self.it_head)
        names = [a["key"] for a in self.api.get(f"/api/requests/{req.pk}/available-actions/").data]
        self.assertIn("verify", names)
        r = self.api.post(f"/api/requests/{req.pk}/actions/", {"action": "return"}, format="json")
        self.assertEqual(r.status_code, 400)              # remarks required
        r = self.api.post(f"/api/requests/{req.pk}/actions/", {"action": "verify"}, format="json")
        self.assertEqual((r.status_code, r.data["status"]), (200, "VERIFIED"))
        self.as_user(self.darta)
        r = self.api.post(f"/api/requests/{req.pk}/actions/", {"action": "register"}, format="json")
        self.assertTrue(r.data["darta_number"])
        r = self.api.post(f"/api/requests/{req.pk}/actions/", {"action": "forward", "to_department": self.dept("KP").pk}, format="json")
        self.assertEqual(r.data["status"], "FORWARDED")
        self.assertEqual(self.api.post(f"/api/requests/{req.pk}/actions/", {"action": "nonsense"}, format="json").status_code, 400)

    def test_timeline_and_scoping(self):
        req = make_request(self.staff)
        perform(req, self.staff, "submit")
        self.as_user(self.it_head)
        tl = self.api.get(f"/api/requests/{req.pk}/timeline/").data
        self.assertEqual([x["action"] for x in tl], ["submit"])
        self.as_user(self.other)
        self.assertEqual(self.api.get(f"/api/requests/{req.pk}/").status_code, 404)
        self.assertEqual(self.api.get("/api/requests/").data["count"], 0)
        self.assertEqual(self.api.post(f"/api/requests/{req.pk}/actions/", {"action": "verify"}, format="json").status_code, 404)

    def test_filtering_search_ordering_pagination(self):
        for i in range(12):
            make_request(self.staff, title=f"Printer {i}", priority="LOW")
        make_request(self.staff, title="Special leave", category="LEAVE", priority="URGENT")
        self.as_user(self.staff)
        r = self.api.get("/api/requests/")
        self.assertEqual((r.data["count"], len(r.data["results"])), (13, 10))
        self.assertIsNotNone(r.data["next"])
        self.assertEqual(self.api.get("/api/requests/", {"q": "special"}).data["count"], 1)
        self.assertEqual(self.api.get("/api/requests/", {"priority": "URGENT"}).data["count"], 1)
        self.assertEqual(self.api.get("/api/requests/", {"category": "LEAVE", "scope": "mine"}).data["count"], 1)
        self.assertEqual(self.api.get("/api/requests/", {"page": 2}).data["results"].__len__(), 3)


class ApiDocumentAndNotificationTests(ApiBase):
    def test_document_upload_download_and_validation(self):
        import shutil, tempfile
        from django.test import override_settings
        tmp = tempfile.mkdtemp()
        try:
            with override_settings(PRIVATE_MEDIA_ROOT=tmp):
                req = make_request(self.staff)
                self.as_user(self.staff)
                pdf = SimpleUploadedFile("a.pdf", b"%PDF-1.4 test")
                r = self.api.post("/api/documents/", {"request": req.pk, "file": pdf, "kind": "SUPPORTING"}, format="multipart")
                self.assertEqual(r.status_code, 201, r.data)
                bad = SimpleUploadedFile("a.exe", b"MZ")
                self.assertEqual(self.api.post("/api/documents/", {"request": req.pk, "file": bad}, format="multipart").status_code, 400)
                dl = self.api.get(f"/api/documents/{r.data['id']}/download/")
                self.assertEqual(dl.status_code, 200)
                self.as_user(self.other)
                self.assertEqual(self.api.get(f"/api/documents/{r.data['id']}/").status_code, 404)
                pdf2 = SimpleUploadedFile("b.pdf", b"%PDF-1.4 test")
                self.assertEqual(self.api.post("/api/documents/", {"request": req.pk, "file": pdf2}, format="multipart").status_code, 403)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_notifications_api(self):
        req = make_request(self.staff)
        perform(req, self.staff, "submit")
        self.as_user(self.it_head)
        data = self.api.get("/api/notifications/").data
        self.assertEqual(data["count"], 1)
        nid = data["results"][0]["id"]
        self.assertEqual(self.api.get("/api/notifications/unread-count/").data, {"unread": 1})
        self.assertTrue(self.api.post(f"/api/notifications/{nid}/mark-read/").data["is_read"])
        self.assertEqual(self.api.get("/api/notifications/unread-count/").data, {"unread": 0})
        self.as_user(self.staff)
        self.assertEqual(self.api.get(f"/api/notifications/{nid}/").status_code, 404)

    def test_workflow_logs_and_annotations_are_read_only_and_scoped(self):
        req = make_request(self.staff)
        perform(req, self.staff, "submit")
        self.as_user(self.it_head)
        self.assertEqual(self.api.get("/api/workflow-logs/", {"request": req.pk}).data["count"], 1)
        self.assertEqual(self.api.post("/api/workflow-logs/", {}, format="json").status_code, 405)
        self.as_user(self.other)
        self.assertEqual(self.api.get("/api/workflow-logs/").data["count"], 0)
        self.assertEqual(self.api.get("/api/annotations/").data["count"], 0)
