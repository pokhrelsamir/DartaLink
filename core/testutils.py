"""Shared helpers for the test-suite."""
from django.test import TestCase, override_settings

from accounts.models import Department, Role, User
from requests_app.models import AdministrativeRequest, Status

PW = "Str0ng-Pass!234"


def make_user(username, role, dept_code, **extra):
    dept = Department.objects.get(code=dept_code) if dept_code else None
    return User.objects.create_user(
        username=username, password=PW, role=role, department=dept,
        first_name=username.title(), last_name="Tester", email=f"{username}@example.test", **extra)


def make_request(user, **kw):
    data = dict(title="Replace UPS batteries", description="The UPS in the server room is failing.",
                category="MAINTENANCE", priority="NORMAL", requester=user, department=user.department,
                status=Status.DRAFT)
    data.update(kw)
    return AdministrativeRequest.objects.create(**data)


@override_settings(SECURE_SSL_REDIRECT=False)
class DartaTestCase(TestCase):
    """Creates one user per role so tests read like the real organisation."""

    @classmethod
    def setUpTestData(cls):
        cls.admin = make_user("admin1", Role.SYSADMIN, None, is_staff=True, is_superuser=True)
        cls.kp = make_user("kp1", Role.KARYALAYA_PRAMUKH, "KP")
        cls.pp = make_user("pp1", Role.PRABIDHIK_PRAMUKH, "PP")
        cls.lp = make_user("lp1", Role.LEKHA_PRAMUKH, "LP")
        cls.rs_head = make_user("rs1", Role.RAJASWA_PRAMUKH, "RS")
        cls.it_head = make_user("it1", Role.IT_PRAMUKH, "IT")
        cls.darta = make_user("darta1", Role.DARTA_STAFF, "DT")
        cls.chalani = make_user("chalani1", Role.CHALANI_STAFF, "CH")
        cls.staff = make_user("staff_it", Role.STAFF, "IT")
        cls.other = make_user("staff_rs", Role.STAFF, "RS")

    def login(self, user):
        self.client.force_login(user)
        return self.client

    def dept(self, code):
        return Department.objects.get(code=code)
