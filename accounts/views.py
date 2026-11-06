from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView, PasswordChangeView
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views.decorators.http import require_POST

from .forms import DepartmentForm, LoginForm, OwnProfileForm, StaffProfileForm, UserForm
from .models import Department, Role, StaffProfile, User
from .permissions import role_required

ADMIN = Role.SYSADMIN


class DartaLoginView(LoginView):
    template_name = "registration/login.html"
    authentication_form = LoginForm
    redirect_authenticated_user = True


class DartaPasswordChangeView(PasswordChangeView):
    template_name = "accounts/password_change.html"
    success_url = reverse_lazy("accounts:profile")

    def form_valid(self, form):
        messages.success(self.request, "Password changed.")
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["breadcrumbs"] = [("Profile", reverse_lazy("accounts:profile")), ("Change password", "")]
        return ctx


@login_required
def profile(request):
    prof, _ = StaffProfile.objects.get_or_create(user=request.user)
    if request.method == "POST":
        messages.info(request, "Profile details are managed by Administration. Only your password can be changed here.")
        return redirect("accounts:profile")
    return render(request, "accounts/profile.html", {
        "profile": prof, "breadcrumbs": [("Profile", "")],
    })


@role_required(ADMIN)
def user_list(request):
    qs = User.objects.select_related("department")
    q = request.GET.get("q", "").strip()
    role = request.GET.get("role", "")
    dept = request.GET.get("department", "")
    if q:
        qs = qs.filter(Q(username__icontains=q) | Q(first_name__icontains=q) | Q(last_name__icontains=q)
                       | Q(staff_id__icontains=q) | Q(email__icontains=q))
    if role:
        qs = qs.filter(role=role)
    if dept:
        qs = qs.filter(department_id=dept)
    page = Paginator(qs, 12).get_page(request.GET.get("page"))
    return render(request, "accounts/user_list.html", {
        "page": page, "roles": Role.choices, "departments": Department.objects.all(),
        "q": q, "role": role, "dept": dept,
        "breadcrumbs": [("Administration", ""), ("Users", "")],
    })


@role_required(ADMIN)
def user_form(request, pk=None):
    instance = get_object_or_404(User, pk=pk) if pk else None
    prof = None
    if instance:
        prof, _ = StaffProfile.objects.get_or_create(user=instance)
    if request.method == "POST":
        form = UserForm(request.POST, instance=instance)
        pform = StaffProfileForm(request.POST, instance=prof)
        if form.is_valid() and pform.is_valid():
            user = form.save()
            profile_obj = pform.save(commit=False)
            profile_obj.user = user
            # a blank profile row is auto-created with every new user: update it
            profile_obj.pk = StaffProfile.objects.get_or_create(user=user)[0].pk
            profile_obj.save()
            messages.success(request, f"User {user.staff_id} saved.")
            return redirect("accounts:user_list")
    else:
        form = UserForm(instance=instance)
        pform = StaffProfileForm(instance=prof)
    return render(request, "accounts/user_form.html", {
        "form": form, "pform": pform, "instance": instance,
        "breadcrumbs": [("Administration", ""), ("Users", reverse_lazy("accounts:user_list")),
                        ("Edit user" if instance else "New user", "")],
    })


@role_required(ADMIN)
@require_POST
def user_toggle(request, pk):
    user = get_object_or_404(User, pk=pk)
    if user == request.user:
        messages.error(request, "You cannot deactivate your own account.")
    else:
        user.is_active = not user.is_active
        user.save(update_fields=["is_active"])
        messages.success(request, f"{user.staff_id} is now {'active' if user.is_active else 'inactive'}.")
    return redirect("accounts:user_list")


@role_required(ADMIN)
def department_list(request):
    return render(request, "accounts/department_list.html", {
        "departments": Department.objects.all(),
        "breadcrumbs": [("Administration", ""), ("Departments", "")],
    })


@role_required(ADMIN)
def department_form(request, pk=None):
    instance = get_object_or_404(Department, pk=pk) if pk else None
    form = DepartmentForm(request.POST or None, instance=instance)
    if request.method == "POST" and form.is_valid():
        dept = form.save()
        messages.success(request, f"Department {dept.name} saved.")
        return redirect("accounts:department_list")
    return render(request, "accounts/department_form.html", {
        "form": form, "instance": instance,
        "breadcrumbs": [("Administration", ""), ("Departments", reverse_lazy("accounts:department_list")),
                        ("Edit" if instance else "New department", "")],
    })
