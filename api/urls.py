from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register("departments", views.DepartmentViewSet, basename="department")
router.register("users", views.UserViewSet, basename="user")
router.register("requests", views.RequestViewSet, basename="request")
router.register("workflow-logs", views.WorkflowLogViewSet, basename="workflowlog")
router.register("annotations", views.AnnotationViewSet, basename="annotation")
router.register("documents", views.DocumentViewSet, basename="document")
router.register("notifications", views.NotificationViewSet, basename="notification")

urlpatterns = [
    path("dashboard/network-status", views.network_status, name="network-status"),
    path("schema/", SpectacularAPIView.as_view(), name="schema"),
    path("docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("", include(router.urls)),
]
