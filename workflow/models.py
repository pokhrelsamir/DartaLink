from django.db import models
from django.contrib.auth.models import AbstractUser
import uuid


class Department(models.TextChoices):
    DARTA_CHALANI = 'DARTA_CHALANI', 'Darta / Chalani Branch'
    KARYALAYA_PRAMUKH = 'KARYALAYA_PRAMUKH', 'Karyalaya Pramukh (Office Head)'
    PRABIDHIK = 'PRABIDHIK', 'Prabidhik Sakha (Technical Branch)'
    LEKHA = 'LEKHA', 'Lekha Sakha (Accounts Branch)'
    RAJASWA = 'RAJASWA', 'Rajaswa Sakha (Revenue Branch)'
    BUDGET = 'BUDGET', 'Budget Sakha (Budget Branch)'
    IT_SAKHA = 'IT_SAKHA', 'IT Sakha (IT / System Admin Branch)'


class CustomUser(AbstractUser):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    department = models.CharField(
        max_length=50,
        choices=Department.choices,
        default=Department.DARTA_CHALANI
    )

    employee_id = models.CharField(
        max_length=20,
        unique=True,
        null=True,
        blank=True
    )

    digital_signature_hash = models.CharField(
        max_length=255,
        null=True,
        blank=True
    )

    # Branch permissions for multi-branch access
    branch_permissions = models.JSONField(
        default=list,
        blank=True
    )

    def has_branch_permission(self, department):
        """
        Check whether the user has permission to access
        the requested department/branch.
        """

        # Superusers have access to every branch.
        if self.is_superuser:
            return True

        # A user's own department is automatically allowed.
        if self.department == department:
            return True

        # Check explicitly assigned branch permissions.
        return department in self.branch_permissions

    def __str__(self):
        return self.username


class Document(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tracking_number = models.CharField(max_length=50, unique=True)
    subject = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    file_url = models.URLField(
        blank=True,
        null=True
    )  # Supabase Storage / Public Link

    created_at = models.DateTimeField(auto_now_add=True)

    created_by = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='created_documents'
    )

    def __str__(self):
        return f"{self.tracking_number} - {self.subject}"


class DartaEntry(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    document = models.OneToOneField(
        Document,
        on_delete=models.CASCADE,
        related_name='darta_details'
    )

    darta_number = models.CharField(
        max_length=50,
        unique=True
    )

    sender_organization = models.CharField(
        max_length=255
    )

    received_date = models.DateField()

    urgency = models.CharField(
        max_length=20,
        choices=[
            ('NORMAL', 'Normal'),
            ('URGENT', 'Urgent'),
            ('IMMEDIATE', 'Immediate')
        ],
        default='NORMAL'
    )


class ChalaniEntry(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    document = models.OneToOneField(
        Document,
        on_delete=models.CASCADE,
        related_name='chalani_details'
    )

    chalani_number = models.CharField(
        max_length=50,
        unique=True
    )

    receiver_organization = models.CharField(
        max_length=255
    )

    dispatch_date = models.DateField(
        auto_now_add=True
    )


class Tippani(models.Model):
    STATUS_CHOICES = [
        ('DRAFT', 'Draft'),
        ('IN_REVIEW', 'In Review'),
        ('TECHNICAL_VERIFIED', 'Technical Verified'),
        ('BUDGET_VERIFIED', 'Budget Verified'),
        ('ACCOUNTS_VERIFIED', 'Accounts Verified'),
        ('REVENUE_VERIFIED', 'Revenue Verified'),
        ('APPROVED', 'Approved by Karyalaya Pramukh'),
        ('REJECTED', 'Rejected'),
        ('DISPATCHED', 'Dispatched via Chalani'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    document = models.ForeignKey(
        Document,
        on_delete=models.CASCADE,
        related_name='tippanis'
    )

    title = models.CharField(
        max_length=255
    )

    status = models.CharField(
        max_length=30,
        choices=STATUS_CHOICES,
        default='IN_REVIEW'
    )

    current_department = models.CharField(
        max_length=50,
        choices=Department.choices,
        default=Department.KARYALAYA_PRAMUKH
    )

    # Financial & Technical Records
    gl_code = models.CharField(
        max_length=50,
        blank=True,
        null=True
    )

    estimated_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00
    )

    tds_deduction = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.00
    )

    net_payable = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )


class WorkflowLog(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    tippani = models.ForeignKey(
        Tippani,
        on_delete=models.CASCADE,
        related_name='logs'
    )

    sender_department = models.CharField(
        max_length=50,
        choices=Department.choices
    )

    receiver_department = models.CharField(
        max_length=50,
        choices=Department.choices
    )

    actor = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True
    )

    action_taken = models.CharField(
        max_length=100
    )

    remarks = models.TextField()

    signature_hash = models.CharField(
        max_length=255,
        blank=True,
        null=True
    )

    timestamp = models.DateTimeField(
        auto_now_add=True
    )