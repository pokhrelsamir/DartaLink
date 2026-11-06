import os
import uuid

from django.conf import settings
from django.db import models

from .storage import PrivateStorage


def upload_path(instance, filename):
    ext = os.path.splitext(filename)[1].lower()
    return f"requests/{instance.request_id}/{uuid.uuid4().hex}{ext}"


class Document(models.Model):
    class Kind(models.TextChoices):
        SUPPORTING = "SUPPORTING", "Supporting document"
        LETTER = "LETTER", "Letter / application"
        OFFICIAL = "OFFICIAL", "Official record"
        CHALANI_COPY = "CHALANI_COPY", "Chalani copy"

    request = models.ForeignKey("requests_app.AdministrativeRequest", on_delete=models.CASCADE,
                                related_name="documents")
    file = models.FileField(upload_to=upload_path, storage=PrivateStorage())
    original_name = models.CharField(max_length=255)
    kind = models.CharField(max_length=14, choices=Kind.choices, default=Kind.SUPPORTING)
    description = models.CharField(max_length=200, blank=True)
    size = models.PositiveIntegerField(default=0)
    content_type = models.CharField(max_length=100, blank=True)
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+")
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-uploaded_at"]

    def __str__(self):
        return self.original_name

    @property
    def extension(self):
        return os.path.splitext(self.original_name)[1].lower().lstrip(".")
