from django.conf import settings
from django.db import models


class WorkflowLog(models.Model):
    """Immutable audit trail: one row per significant action."""
    request = models.ForeignKey("requests_app.AdministrativeRequest", on_delete=models.CASCADE, related_name="logs")
    action = models.CharField(max_length=30)
    from_status = models.CharField(max_length=14, blank=True)
    to_status = models.CharField(max_length=14, blank=True)
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+")
    from_department = models.ForeignKey("accounts.Department", null=True, blank=True,
                                        on_delete=models.SET_NULL, related_name="+")
    to_department = models.ForeignKey("accounts.Department", null=True, blank=True,
                                      on_delete=models.SET_NULL, related_name="+")
    remarks = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at", "id"]

    def __str__(self):
        return f"{self.request.request_number}: {self.action}"


class Annotation(models.Model):
    """Authority input on a request: recommendation, tippani (file note) or Tok Aadesh (order)."""
    class Kind(models.TextChoices):
        RECOMMENDATION = "RECOMMENDATION", "Recommendation"
        TIPPANI = "TIPPANI", "Tippani"
        TOK_AADESH = "TOK_AADESH", "Tok Aadesh"

    request = models.ForeignKey("requests_app.AdministrativeRequest", on_delete=models.CASCADE,
                                related_name="annotations")
    kind = models.CharField(max_length=16, choices=Kind.choices)
    text = models.TextField()
    author = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+")
    department = models.ForeignKey("accounts.Department", null=True, on_delete=models.SET_NULL, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at", "id"]
