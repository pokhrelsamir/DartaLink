from django.contrib.auth.models import AbstractUser, UserManager as DjangoUserManager
from django.db import models
from django.urls import reverse


class Department(models.Model):
    """An office / section.  Can be added dynamically from the UI or admin."""

    name = models.CharField(max_length=120, unique=True)
    name_np = models.CharField("Name (Nepali)", max_length=120, blank=True)
    code = models.CharField(
        max_length=6, unique=True,
        help_text="Short code used in staff IDs, e.g. KP -> NTC-KP-001.",
    )
    description = models.TextField(blank=True)
    is_authority = models.BooleanField(
        default=False,
        help_text="Requests can be forwarded here for review, recommendation or decision.",
    )
    is_registry = models.BooleanField(
        default=False, help_text="Registry office (Darta / Chalani).",
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def save(self, *args, **kwargs):
        self.code = (self.code or "").strip().upper()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("accounts:department_edit", args=[self.pk])


class Role(models.TextChoices):
    SYSADMIN = "SYSADMIN", "System Administrator"
    KARYALAYA_PRAMUKH = "KARYALAYA_PRAMUKH", "Karyalaya Pramukh"
    PRABIDHIK_PRAMUKH = "PRABIDHIK_PRAMUKH", "Prabidhik Pramukh"
    LEKHA_PRAMUKH = "LEKHA_PRAMUKH", "Lekha Pramukh"
    RAJASWA_PRAMUKH = "RAJASWA_PRAMUKH", "Rajaswa Sakha Pramukh"
    BUDGET_PRAMUKH = "BUDGET_PRAMUKH", "Budget Sakha Pramukh"
    IT_PRAMUKH = "IT_PRAMUKH", "IT Sakha Pramukh"
    SECTION_PRAMUKH = "SECTION_PRAMUKH", "Section Pramukh (other)"
    DARTA_STAFF = "DARTA_STAFF", "Darta Staff"
    CHALANI_STAFF = "CHALANI_STAFF", "Chalani Staff"
    STAFF = "STAFF", "Section Staff"


PRAMUKH_ROLES = {
    Role.KARYALAYA_PRAMUKH, Role.PRABIDHIK_PRAMUKH, Role.LEKHA_PRAMUKH,
    Role.RAJASWA_PRAMUKH, Role.BUDGET_PRAMUKH, Role.IT_PRAMUKH, Role.SECTION_PRAMUKH,
}
# Role -> required department code (generic roles are not listed)
ROLE_DEPT_CODE = {
    Role.KARYALAYA_PRAMUKH: "KP", Role.PRABIDHIK_PRAMUKH: "PP", Role.LEKHA_PRAMUKH: "LP",
    Role.RAJASWA_PRAMUKH: "RS", Role.BUDGET_PRAMUKH: "BS", Role.IT_PRAMUKH: "IT",
    Role.DARTA_STAFF: "DT", Role.CHALANI_STAFF: "CH",
}


def generate_staff_id(department):
    code = department.code if department else "SA"
    prefix = f"NTC-{code}-"
    highest = 0
    for sid in User.objects.filter(staff_id__startswith=prefix).values_list("staff_id", flat=True):
        tail = sid[len(prefix):]
        if tail.isdigit():
            highest = max(highest, int(tail))
    return f"{prefix}{highest + 1:03d}"


class UserManager(DjangoUserManager):
    def create_superuser(self, username, email=None, password=None, **extra_fields):
        extra_fields.setdefault("role", Role.SYSADMIN)
        return super().create_superuser(username, email, password, **extra_fields)


class User(AbstractUser):
    staff_id = models.CharField(max_length=20, unique=True, blank=True, editable=False)
    role = models.CharField(max_length=24, choices=Role.choices, default=Role.STAFF)
    department = models.ForeignKey(
        Department, null=True, blank=True, on_delete=models.PROTECT, related_name="members",
    )

    objects = UserManager()

    class Meta:
        ordering = ["staff_id"]

    def save(self, *args, **kwargs):
        if not self.staff_id:
            self.staff_id = generate_staff_id(self.department)
        super().save(*args, **kwargs)

    # --- convenience -----------------------------------------------------
    @property
    def display_name(self):
        return self.get_full_name() or self.username

    @property
    def initials(self):
        parts = self.display_name.split()
        return "".join(p[0] for p in parts[:2]).upper() or "?"

    @property
    def is_sysadmin(self):
        return self.role == Role.SYSADMIN

    @property
    def is_pramukh(self):
        return self.role in PRAMUKH_ROLES

    @property
    def is_karyalaya_pramukh(self):
        return self.role == Role.KARYALAYA_PRAMUKH

    @property
    def is_darta(self):
        return self.role == Role.DARTA_STAFF

    @property
    def is_chalani(self):
        return self.role == Role.CHALANI_STAFF

    @property
    def can_create_requests(self):
        return self.is_active and self.role != Role.SYSADMIN

    def __str__(self):
        return f"{self.display_name} ({self.staff_id})"


class StaffProfile(models.Model):
    EMPLOYMENT = [("PERMANENT", "Permanent"), ("CONTRACT", "Contract"), ("TEMPORARY", "Temporary")]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    designation = models.CharField(max_length=120, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    office_location = models.CharField(max_length=120, blank=True)
    employment_type = models.CharField(max_length=12, choices=EMPLOYMENT, default="PERMANENT")
    joined_on = models.DateField(null=True, blank=True)
    emergency_contact = models.CharField(max_length=120, blank=True)
    address = models.CharField(max_length=200, blank=True)

    def __str__(self):
        return f"Profile of {self.user.username}"
