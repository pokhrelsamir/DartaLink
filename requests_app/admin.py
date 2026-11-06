from django.contrib import admin
from django import forms
from django.core.exceptions import ValidationError

from documents.models import Document
from documents.validators import validate_upload
from workflow.models import Annotation, WorkflowLog

from .models import AdministrativeRequest, Sequence


class LogInline(admin.TabularInline):
    model = WorkflowLog
    extra = 0
    can_delete = False
    readonly_fields = ("action", "from_status", "to_status", "actor", "from_department", "to_department",
                       "remarks", "created_at")

    def has_add_permission(self, request, obj=None):
        return False


class DocumentInlineForm(forms.ModelForm):
    class Meta:
        model = Document
        fields = ("file", "kind", "description")

    def clean_file(self):
        uploaded_file = self.cleaned_data.get("file")
        if uploaded_file:
            try:
                validate_upload(uploaded_file)
            except ValidationError as exc:
                raise forms.ValidationError(exc.messages)
        return uploaded_file


class DocumentInline(admin.TabularInline):
    model = Document
    form = DocumentInlineForm
    extra = 1
    fields = ("file", "kind", "description", "original_name", "size", "content_type", "uploaded_by", "uploaded_at")
    readonly_fields = ("original_name", "size", "content_type", "uploaded_by", "uploaded_at")

    def save_formset(self, request, form, formset, change):
        instances = formset.save(commit=False)
        for instance in instances:
            uploaded_file = instance.file
            instance.original_name = uploaded_file.name[:255]
            instance.size = uploaded_file.size
            instance.content_type = (getattr(uploaded_file, "content_type", "") or "")[:100]
            instance.uploaded_by = request.user
            instance.save()
        formset.save_m2m()


@admin.register(AdministrativeRequest)
class RequestAdmin(admin.ModelAdmin):
    list_display = ("request_number", "title", "status", "category", "priority", "requester", "department",
                    "current_department", "darta_number", "chalani_number", "created_at")
    list_filter = ("status", "category", "priority", "department", "current_department")
    search_fields = ("request_number", "title", "darta_number", "chalani_number",
                     "requester__username", "requester__staff_id")
    date_hierarchy = "created_at"
    readonly_fields = ("request_number", "created_at", "updated_at")
    inlines = [DocumentInline, LogInline]


@admin.register(Sequence)
class SequenceAdmin(admin.ModelAdmin):
    list_display = ("key", "value")


@admin.register(WorkflowLog)
class WorkflowLogAdmin(admin.ModelAdmin):
    list_display = ("request", "action", "from_status", "to_status", "actor", "created_at")
    list_filter = ("action", "to_status")
    search_fields = ("request__request_number", "remarks", "actor__username")

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Annotation)
class AnnotationAdmin(admin.ModelAdmin):
    list_display = ("request", "kind", "author", "department", "created_at")
    list_filter = ("kind",)
