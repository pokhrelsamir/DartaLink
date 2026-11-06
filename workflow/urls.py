from django.urls import path

from . import views

app_name = "workflow"
urlpatterns = [path("audit/", views.audit_log, name="audit")]
