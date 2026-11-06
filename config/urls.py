from django.contrib import admin
from django.urls import include, path

from core import views as core_views

admin.site.site_header = "DartaLink administration"
admin.site.site_title = "DartaLink admin"

urlpatterns = [
    path("", include("dashboard.urls")),
    path("accounts/", include("accounts.urls")),
    path("requests/", include("requests_app.urls")),
    path("workflow/", include("workflow.urls")),
    path("documents/", include("documents.urls")),
    path("notifications/", include("notifications.urls")),
    path("api/", include("api.urls")),
    path("admin/", admin.site.urls),
]

handler400 = core_views.error_400
handler403 = core_views.error_403
handler404 = core_views.error_404
handler500 = core_views.error_500
