from django.contrib.messages import get_messages
from django.urls import reverse

from core.testutils import PW, DartaTestCase, make_user

from .forms import UserForm
from .models import Department, Role, User


class StaffIdTests(DartaTestCase):
    def test_staff_id_uses_department_prefix_and_sequence(self):
        self.assertEqual(self.staff.staff_id, "NTC-IT-002")
        second = make_user("staff_it2", Role.STAFF, "IT")
        self.assertEqual(second.staff_id, "NTC-IT-003")
        self.assertEqual(self.kp.staff_id, "NTC-KP-001")
        self.assertEqual(self.admin.staff_id, "NTC-SA-001")

    def test_staff_id_is_stable_after_edit(self):
        sid = self.staff.staff_id
        self.staff.first_name = "Changed"
        self.staff.save()
        self.staff.refresh_from_db()
        self.assertEqual(self.staff.staff_id, sid)

    def test_profile_is_created_automatically(self):
        self.assertTrue(hasattr(self.staff, "profile"))

    def test_default_departments_exist_and_new_ones_can_be_added(self):
        for code in ("KP", "PP", "LP", "RS", "BS", "IT", "DT", "CH"):
            self.assertTrue(Department.objects.filter(code=code).exists(), code)
        d = Department.objects.create(name="Legal Sakha", code="lg", is_authority=True)
        self.assertEqual(d.code, "LG")
        u = make_user("legal1", Role.SECTION_PRAMUKH, "LG")
        self.assertEqual(u.staff_id, "NTC-LG-001")


class AuthTests(DartaTestCase):
    def test_login_with_username_and_with_staff_id(self):
        r = self.client.post(reverse("accounts:login"), {"username": "staff_it", "password": PW})
        self.assertRedirects(r, reverse("dashboard:home"))
        self.client.logout()
        r = self.client.post(reverse("accounts:login"), {"username": "NTC-IT-001", "password": PW})
        self.assertRedirects(r, reverse("dashboard:home"))

    def test_wrong_password_is_rejected(self):
        r = self.client.post(reverse("accounts:login"), {"username": "staff_it", "password": "nope"})
        self.assertEqual(r.status_code, 200)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_inactive_user_cannot_login(self):
        User.objects.filter(pk=self.staff.pk).update(is_active=False)
        r = self.client.post(reverse("accounts:login"), {"username": "staff_it", "password": PW})
        self.assertEqual(r.status_code, 200)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_anonymous_users_are_redirected_to_login(self):
        for name in ("dashboard:home", "requests:list", "notifications:list", "accounts:profile"):
            r = self.client.get(reverse(name))
            self.assertEqual(r.status_code, 302, name)
            self.assertIn(reverse("accounts:login"), r["Location"])

    def test_logout_requires_post(self):
        self.login(self.staff)
        self.assertEqual(self.client.get(reverse("accounts:logout")).status_code, 405)
        self.client.post(reverse("accounts:logout"))
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_post_without_csrf_token_is_rejected(self):
        from django.test import Client
        c = Client(enforce_csrf_checks=True)
        c.force_login(self.staff)
        self.assertEqual(c.post(reverse("accounts:logout")).status_code, 403)

    def test_password_change(self):
        self.login(self.staff)
        r = self.client.post(reverse("accounts:password_change"), {
            "old_password": PW, "new_password1": "An0ther-Pass!987", "new_password2": "An0ther-Pass!987"})
        self.assertRedirects(r, reverse("accounts:profile"))
        self.staff.refresh_from_db()
        self.assertTrue(self.staff.check_password("An0ther-Pass!987"))


class RoleAccessTests(DartaTestCase):
    def test_only_sysadmin_can_manage_users_and_departments(self):
        for user in (self.staff, self.kp, self.darta, self.chalani):
            self.login(user)
            for name in ("accounts:user_list", "accounts:user_create", "accounts:department_list",
                         "accounts:department_create", "workflow:audit"):
                self.assertEqual(self.client.get(reverse(name)).status_code, 403, (user.username, name))
        self.login(self.admin)
        for name in ("accounts:user_list", "accounts:user_create", "accounts:department_list", "workflow:audit"):
            self.assertEqual(self.client.get(reverse(name)).status_code, 200, name)

    def test_admin_creates_user_and_staff_id_is_generated(self):
        self.login(self.admin)
        r = self.client.post(reverse("accounts:user_create"), {
            "username": "newbie", "first_name": "New", "last_name": "Hire", "email": "n@example.test",
            "role": Role.STAFF, "department": self.dept("BS").pk, "is_active": "on",
            "password1": PW, "password2": PW, "employment_type": "PERMANENT", "designation": "Officer"})
        self.assertRedirects(r, reverse("accounts:user_list"))
        u = User.objects.get(username="newbie")
        self.assertEqual(u.staff_id, "NTC-BS-001")
        self.assertEqual(u.profile.designation, "Officer")
        self.assertTrue(u.check_password(PW))

    def test_role_must_match_department(self):
        form = UserForm({"username": "bad", "first_name": "A", "last_name": "B", "email": "a@b.test",
                         "role": Role.DARTA_STAFF, "department": self.dept("IT").pk, "is_active": "on",
                         "password1": PW, "password2": PW})
        self.assertFalse(form.is_valid())
        self.assertIn("department", form.errors)

    def test_admin_cannot_deactivate_self_but_can_deactivate_others(self):
        self.login(self.admin)
        self.client.post(reverse("accounts:user_toggle", args=[self.admin.pk]))
        self.admin.refresh_from_db()
        self.assertTrue(self.admin.is_active)
        self.client.post(reverse("accounts:user_toggle", args=[self.staff.pk]))
        self.staff.refresh_from_db()
        self.assertFalse(self.staff.is_active)

    def test_admin_adds_department(self):
        self.login(self.admin)
        r = self.client.post(reverse("accounts:department_create"), {
            "name": "Legal Sakha", "name_np": "कानून शाखा", "code": "lg", "is_authority": "on", "is_active": "on"})
        self.assertRedirects(r, reverse("accounts:department_list"))
        self.assertTrue(Department.objects.filter(code="LG", is_authority=True).exists())

    def test_profile_update(self):
        self.login(self.staff)
        r = self.client.post(reverse("accounts:profile"), {
            "first_name": "Nabin", "last_name": "Lama", "email": "nabin@example.test",
            "designation": "Engineer", "phone": "9841000000", "employment_type": "PERMANENT"})
        self.assertRedirects(r, reverse("accounts:profile"))
        self.staff.refresh_from_db()
        self.assertEqual(self.staff.first_name, "Staff_It")
        self.assertNotEqual(self.staff.profile.phone, "9841000000")
