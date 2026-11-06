from django.urls import path

from workflow.views import action

from . import views

app_name = "requests"
urlpatterns = [
    path("", views.request_list, name="list"),
    path("report/", views.request_report, name="report"),
    path("report/pdf/", views.request_report_pdf, name="report_pdf"),
    path("new/", views.request_create, name="create"),
    path("<int:pk>/", views.request_detail, name="detail"),
    path("<int:pk>/confirmation/", views.approval_confirmation, name="approval_confirmation"),
    path("<int:pk>/edit/", views.request_edit, name="edit"),
    path("<int:pk>/action/<slug:key>/", action, name="action"),
]
