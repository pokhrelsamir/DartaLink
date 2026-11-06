from django.contrib import admin

from .models import Document


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ("original_name", "request", "kind", "size", "uploaded_by", "uploaded_at")
    list_filter = ("kind",)
    search_fields = ("original_name", "request__request_number")
    readonly_fields = ("uploaded_at", "size", "content_type")
