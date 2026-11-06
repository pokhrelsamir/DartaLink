from django.conf import settings
from django.db import models, transaction
from django.urls import reverse
from django.utils import timezone


class Sequence(models.Model):
    """Gap-free-ish counters for request / darta / chalani numbers."""
    key = models.CharField(max_length=60, unique=True)
    value = models.PositiveIntegerField(default=0)

    @classmethod
    def next(cls, key):
        with transaction.atomic():
            seq, _ = cls.objects.select_for_update().get_or_create(key=key)
            seq.value += 1
            seq.save(update_fields=["value"])
            return seq.value


class Status(models.TextChoices):
    DRAFT = "DRAFT", "Draft"
    SUBMITTED = "SUBMITTED", "Awaiting verification"
    BRANCH_REVIEW = "BRANCH_REVIEW", "Branch review"
    VERIFIED = "VERIFIED", "Verified – awaiting Darta"
    RETURNED = "RETURNED", "Returned for revision"
    REGISTERED = "REGISTERED", "Registered (Darta)"
    FORWARDED = "FORWARDED", "Forwarded"
    UNDER_REVIEW = "UNDER_REVIEW", "Under review"
    APPROVED = "APPROVED", "Approved"
    REJECTED = "REJECTED", "Rejected"
    PROCESSING = "PROCESSING", "Processing"
    DISPATCHED = "DISPATCHED", "Dispatched (Chalani)"
    COMPLETED = "COMPLETED", "Completed"
    CANCELLED = "CANCELLED", "Cancelled"


EDITABLE = {Status.DRAFT, Status.RETURNED}
TERMINAL = {Status.REJECTED, Status.COMPLETED, Status.CANCELLED}
IN_AUTHORITY = {Status.FORWARDED, Status.UNDER_REVIEW}
DARTA_VISIBLE = {Status.VERIFIED, Status.REGISTERED, Status.FORWARDED, Status.UNDER_REVIEW,
                 Status.APPROVED, Status.REJECTED, Status.PROCESSING, Status.DISPATCHED, Status.COMPLETED}
CHALANI_VISIBLE = {Status.APPROVED, Status.PROCESSING, Status.DISPATCHED, Status.COMPLETED}
POST_REGISTRATION = {Status.REGISTERED, Status.FORWARDED, Status.UNDER_REVIEW, Status.APPROVED,
                     Status.REJECTED, Status.PROCESSING, Status.DISPATCHED, Status.COMPLETED}
# stages shown in the progress tracker on the detail page
PIPELINE = [
    ("Submitted", {Status.SUBMITTED}),
    ("Branch review", {Status.BRANCH_REVIEW}),
    ("Verified", {Status.VERIFIED}),
    ("Registered", {Status.REGISTERED}),
    ("Review", {Status.FORWARDED, Status.UNDER_REVIEW}),
    ("Decision", {Status.APPROVED, Status.REJECTED}),
    ("Chalani", {Status.PROCESSING, Status.DISPATCHED}),
    ("Completed", {Status.COMPLETED}),
]


class Category(models.TextChoices):
    LEAVE = "LEAVE", "Leave"
    PROCUREMENT = "PROCUREMENT", "Procurement"
    BUDGET = "BUDGET", "Budget / finance"
    IT_SUPPORT = "IT_SUPPORT", "IT support"
    TRANSFER = "TRANSFER", "Transfer / deputation"
    TRAINING = "TRAINING", "Training"
    MAINTENANCE = "MAINTENANCE", "Maintenance / repair"
    OTHER = "OTHER", "Other"


class Priority(models.TextChoices):
    LOW = "LOW", "Low"
    NORMAL = "NORMAL", "Normal"
    HIGH = "HIGH", "High"
    URGENT = "URGENT", "Urgent"


class AdministrativeRequest(models.Model):
    request_number = models.CharField(max_length=30, unique=True, editable=False)
    title = models.CharField(max_length=200)
    category = models.CharField(max_length=20, choices=Category.choices, default=Category.OTHER)
    priority = models.CharField(max_length=10, choices=Priority.choices, default=Priority.NORMAL)
    description = models.TextField()
    customer_name = models.CharField(max_length=160, blank=True)
    customer_contact = models.CharField(max_length=10, blank=True)
    intake_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                                  on_delete=models.SET_NULL, related_name="requests_intaken")
    requested_amount = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    required_by = models.DateField(null=True, blank=True)

    requester = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="requests_made")
    department = models.ForeignKey("accounts.Department", on_delete=models.PROTECT, related_name="requests_originated")
    status = models.CharField(max_length=14, choices=Status.choices, default=Status.DRAFT, db_index=True)
    current_department = models.ForeignKey(
        "accounts.Department", null=True, blank=True, on_delete=models.SET_NULL, related_name="requests_held")

    # Darta (inward registration)
    darta_number = models.CharField(max_length=30, blank=True, db_index=True)
    darta_date = models.DateField(null=True, blank=True)
    registered_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                                      on_delete=models.SET_NULL, related_name="+")
    branch_verified_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                                           on_delete=models.SET_NULL, related_name="+")
    branch_verified_at = models.DateTimeField(null=True, blank=True)
    # Decision
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                                    on_delete=models.SET_NULL, related_name="+")
    approved_at = models.DateTimeField(null=True, blank=True)
    decision_remarks = models.TextField(blank=True)
    # Chalani (outward dispatch)
    chalani_number = models.CharField(max_length=30, blank=True, db_index=True)
    chalani_date = models.DateField(null=True, blank=True)
    dispatched_to = models.CharField(max_length=200, blank=True)
    dispatched_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                                      on_delete=models.SET_NULL, related_name="+")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [models.Index(fields=["status", "current_department"])]

    def save(self, *args, **kwargs):
        if not self.request_number:
            year = timezone.localdate().year
            self.request_number = f"DL-REQ-{year}-{Sequence.next(f'request-{year}'):05d}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.request_number} – {self.title}"

    def get_absolute_url(self):
        return reverse("requests:detail", args=[self.pk])

    # --- stage-driven field availability --------------------------------
    @property
    def is_editable_stage(self):
        return self.status in EDITABLE

    @property
    def is_terminal(self):
        return self.status in TERMINAL

    def can_edit(self, user):
        return user.is_authenticated and user.pk == self.requester_id and self.is_editable_stage

    @property
    def badge_class(self):
        return {
            "DRAFT": "neutral", "SUBMITTED": "info", "BRANCH_REVIEW": "purple", "VERIFIED": "info", "RETURNED": "warn",
            "REGISTERED": "info", "FORWARDED": "info", "UNDER_REVIEW": "purple",
            "APPROVED": "ok", "REJECTED": "danger", "PROCESSING": "purple",
            "DISPATCHED": "ok", "COMPLETED": "ok", "CANCELLED": "neutral",
        }.get(self.status, "neutral")

    @property
    def stage_index(self):
        for i, (_, statuses) in enumerate(PIPELINE):
            if self.status in statuses:
                return i
        return -1
