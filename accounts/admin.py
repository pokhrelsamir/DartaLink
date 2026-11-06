from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import Department, StaffProfile, User


class ProfileInline(admin.StackedInline):
    model = StaffProfile
    can_delete = False


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ("staff_id", "username", "get_full_name", "role", "department", "is_active")
    list_filter = ("role", "department", "is_active")
    search_fields = ("staff_id", "username", "first_name", "last_name", "email")
    readonly_fields = ("staff_id", "last_login", "date_joined")
    inlines = [ProfileInline]
    fieldsets = BaseUserAdmin.fieldsets + (("DartaLink", {"fields": ("staff_id", "role", "department")}),)
    add_fieldsets = BaseUserAdmin.add_fieldsets + (("DartaLink", {"fields": ("role", "department")}),)


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "name_np", "is_authority", "is_registry", "is_active")
    list_filter = ("is_authority", "is_registry", "is_active")
    search_fields = ("name", "name_np", "code")
