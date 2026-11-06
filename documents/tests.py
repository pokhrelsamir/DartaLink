import os
import shutil
import tempfile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import reverse

from core.testutils import DartaTestCase, make_request
from requests_app.models import Status
from workflow.services import perform

from .models import Document

TMP = tempfile.mkdtemp(prefix="dartalink-test-")
PDF = b"%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF"


@override_settings(PRIVATE_MEDIA_ROOT=TMP)
class DocumentTests(DartaTestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TMP, ignore_errors=True)

    def setUp(self):
        self.req = make_request(self.staff)
        self.upload_url = reverse("documents:upload", args=[self.req.pk])

    def upload(self, name="quote.pdf", content=PDF, **extra):
        return self.client.post(self.upload_url, {"files": SimpleUploadedFile(name, content), **extra})

    def test_upload_stores_file_privately_with_random_name(self):
        self.login(self.staff)
        self.upload(description="Vendor quote")
        doc = Document.objects.get()
        self.assertEqual((doc.original_name, doc.request, doc.uploaded_by, doc.size), ("quote.pdf", self.req, self.staff, len(PDF)))
        self.assertTrue(os.path.abspath(doc.file.path).startswith(os.path.abspath(TMP)))
        self.assertNotIn("quote", os.path.basename(doc.file.name))

    def test_disallowed_extension_and_fake_content_are_rejected(self):
        self.login(self.staff)
        self.upload("shell.exe", b"MZ\x90\x00")
        self.upload("fake.pdf", b"this is not a pdf")
        self.upload("empty.txt", b"")
        self.assertFalse(Document.objects.exists())

    @override_settings(MAX_UPLOAD_MB=0)
    def test_size_limit(self):
        self.login(self.staff)
        self.upload()
        self.assertFalse(Document.objects.exists())

    def test_download_requires_access_to_the_request(self):
        self.login(self.staff)
        self.upload()
        doc = Document.objects.get()
        url = reverse("documents:download", args=[doc.pk])
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(b"".join(r.streaming_content), PDF)
        self.assertIn("attachment", r["Content-Disposition"])
        self.assertEqual(self.login(self.other).get(url).status_code, 404)
        self.assertEqual(self.login(self.rs_head).get(url).status_code, 404)
        self.client.logout()
        self.assertEqual(self.client.get(url).status_code, 302)

    def test_view_streams_inline_and_requires_access_to_the_request(self):
        self.login(self.staff)
        self.upload("preview.pdf")
        doc = Document.objects.get()
        url = reverse("documents:view", args=[doc.pk])
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(b"".join(r.streaming_content), PDF)
        self.assertIn("inline", r["Content-Disposition"])
        self.assertEqual(self.login(self.other).get(url).status_code, 404)
        self.client.logout()
        self.assertEqual(self.client.get(url).status_code, 302)

    def test_colleagues_in_the_workflow_can_download_after_submission(self):
        self.login(self.staff)
        self.upload()
        doc = Document.objects.get()
        perform(self.req, self.staff, "submit")
        self.assertEqual(self.login(self.it_head).get(reverse("documents:download", args=[doc.pk])).status_code, 200)

    def test_upload_permissions_follow_the_stage(self):
        perform(self.req, self.staff, "submit")
        # the requester can no longer add files once submitted
        self.assertEqual(self.login(self.staff).post(self.upload_url, {"files": SimpleUploadedFile("a.pdf", PDF)}).status_code, 403)
        # a Pramukh in the workflow can
        self.login(self.it_head)
        self.upload("section-note.pdf")
        self.assertEqual(Document.objects.count(), 1)
        # an outsider cannot even see the request
        self.assertEqual(self.login(self.other).post(self.upload_url, {"files": SimpleUploadedFile("a.pdf", PDF)}).status_code, 404)

    def test_system_administrator_can_add_later_supporting_documents(self):
        self.req.status = Status.COMPLETED
        self.req.save(update_fields=["status"])
        self.login(self.admin)
        response = self.client.post(self.upload_url, {
            "files": SimpleUploadedFile("admin-note.pdf", PDF),
            "kind": Document.Kind.SUPPORTING,
            "description": "Additional document added by administration.",
        })
        self.assertRedirects(response, self.req.get_absolute_url())
        document = Document.objects.get()
        self.assertEqual(document.uploaded_by, self.admin)
        self.assertEqual(document.description, "Additional document added by administration.")
        detail = self.client.get(self.req.get_absolute_url())
        self.assertContains(detail, "Add documents")

    def test_delete_rules(self):
        self.login(self.staff)
        self.upload()
        doc = Document.objects.get()
        path = doc.file.path
        self.assertEqual(self.login(self.other).post(reverse("documents:delete", args=[doc.pk])).status_code, 404)
        self.login(self.staff)
        self.client.post(reverse("documents:delete", args=[doc.pk]))
        self.assertFalse(Document.objects.exists())
        self.assertFalse(os.path.exists(path))

    def test_cannot_delete_after_submission(self):
        self.login(self.staff)
        self.upload()
        doc = Document.objects.get()
        perform(self.req, self.staff, "submit")
        self.assertEqual(self.client.post(reverse("documents:delete", args=[doc.pk])).status_code, 403)

    def test_create_view_accepts_attachments(self):
        self.login(self.staff)
        r = self.client.post(reverse("requests:create"), {
            "title": "With file", "category": "OTHER", "priority": "NORMAL", "description": "d",
            "files": SimpleUploadedFile("spec.pdf", PDF), "save": "1"})
        self.assertEqual(r.status_code, 302)
        self.assertEqual(Document.objects.get().request.title, "With file")
