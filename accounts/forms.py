from django import forms
from django.contrib.auth import password_validation
from django.contrib.auth.forms import AuthenticationForm

from .models import ROLE_DEPT_CODE, Department, Role, StaffProfile, User


class LoginForm(AuthenticationForm):
    username = forms.CharField(
        label="Username or Staff ID",
        widget=forms.TextInput(attrs={"autofocus": True, "autocomplete": "username"}),
    )

    def clean(self):
        # allow signing in with the staff ID as well as the username
        raw = self.cleaned_data.get("username")
        if raw:
            match = User.objects.filter(staff_id__iexact=raw.strip()).first()
            if match:
                self.cleaned_data["username"] = match.get_username()
        return super().clean()


class UserForm(forms.ModelForm):
    password1 = forms.CharField(label="Password", widget=forms.PasswordInput, required=False)
    password2 = forms.CharField(label="Confirm password", widget=forms.PasswordInput, required=False)

    class Meta:
        model = User
        fields = ["username", "first_name", "last_name", "email", "role", "department", "is_active"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["department"].queryset = Department.objects.filter(is_active=True)
        self.fields["email"].required = True
        self.fields["first_name"].required = True

    def clean(self):
        data = super().clean()
        role, dept = data.get("role"), data.get("department")
        needed = ROLE_DEPT_CODE.get(role)
        if needed and (not dept or dept.code != needed):
            self.add_error("department", f"{Role(role).label} must belong to the department with code {needed}.")
        if role not in (Role.SYSADMIN,) and not dept:
            self.add_error("department", "Choose a department for this role.")
        p1, p2 = data.get("password1"), data.get("password2")
        if not self.instance.pk and not p1:
            self.add_error("password1", "A password is required for new users.")
        if p1 or p2:
            if p1 != p2:
                self.add_error("password2", "Passwords do not match.")
            else:
                try:
                    password_validation.validate_password(p1, self.instance)
                except forms.ValidationError as exc:
                    self.add_error("password1", exc)
        return data

    def save(self, commit=True):
        user = super().save(commit=False)
        if self.cleaned_data.get("password1"):
            user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
        return user


class StaffProfileForm(forms.ModelForm):
    class Meta:
        model = StaffProfile
        fields = ["designation", "phone", "office_location", "employment_type",
                  "joined_on", "emergency_contact", "address"]
        widgets = {"joined_on": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d")}


class OwnProfileForm(forms.ModelForm):
    """Fields a user may change about themself."""
    class Meta:
        model = User
        fields = ["first_name", "last_name", "email"]


class DepartmentForm(forms.ModelForm):
    class Meta:
        model = Department
        fields = ["name", "name_np", "code", "description", "is_authority", "is_registry", "is_active"]
        widgets = {"description": forms.Textarea(attrs={"rows": 3})}

    def clean_code(self):
        return self.cleaned_data["code"].strip().upper()
