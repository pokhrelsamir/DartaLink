from django.core.exceptions import ValidationError as DjangoValidationError
from django.http import FileResponse, Http404
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import mixins, permissions, status, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response

from network_telemetry.ping_checker import client_ping

from accounts.models import Department, User
from documents.models import Document
from documents.services import can_delete, can_upload
from notifications.models import Notification
from requests_app.filters import apply_filters
from requests_app.models import AdministrativeRequest, Status
from requests_app.selectors import action_queue, visible_requests
from workflow.models import Annotation, WorkflowLog
from workflow.services import ACTIONS, Invalid, NotAllowed, available_actions, perform

from . import serializers as s


class IsSysadminOrReadOnly(permissions.BasePermission):
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        return request.method in permissions.SAFE_METHODS or request.user.is_sysadmin


@extend_schema(
    responses={
        200: OpenApiTypes.OBJECT,
        400: OpenApiTypes.OBJECT,
        503: OpenApiTypes.OBJECT,
    },
    description="Return the live ICMP RTT from the server to the authenticated client address.",
)
@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def network_status(request):
    try:
        result = client_ping(request)
    except ValueError:
        return Response({"detail": "The client address is not a valid IP address."},
                        status=status.HTTP_400_BAD_REQUEST)

    response_status = status.HTTP_200_OK if result["reachable"] else status.HTTP_503_SERVICE_UNAVAILABLE
    return Response(
        {
            "client_ip": result["host"],
            "reachable": result["reachable"],
            "latency_ms": result["latency_ms"],
            "error": result["error"],
        },
        status=response_status,
    )


class DepartmentViewSet(viewsets.ModelViewSet):
    """Departments / sections. Anyone signed in can read; only System Administrators can change."""
    serializer_class = s.DepartmentSerializer
    permission_classes = [IsSysadminOrReadOnly]
    queryset = Department.objects.all()
    search_fields = ["name", "name_np", "code"]
    ordering_fields = ["name", "code"]


class UserViewSet(viewsets.ModelViewSet):
    """Staff directory. Read-only for everyone signed in; System Administrators can create and edit."""
    permission_classes = [IsSysadminOrReadOnly]
    search_fields = ["username", "first_name", "last_name", "staff_id"]
    ordering_fields = ["staff_id", "username"]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return User.objects.none()
        qs = User.objects.select_related("department")
        if not self.request.user.is_sysadmin:
            qs = qs.filter(is_active=True)
        role, dept = self.request.query_params.get("role"), self.request.query_params.get("department")
        if role:
            qs = qs.filter(role=role)
        if dept and dept.isdigit():
            qs = qs.filter(department_id=int(dept))
        return qs

    def get_serializer_class(self):
        return s.UserSerializer if self.request.method in permissions.SAFE_METHODS else s.UserWriteSerializer

    @extend_schema(responses=s.UserSerializer)
    @action(detail=False, methods=["get"], permission_classes=[permissions.IsAuthenticated])
    def me(self, request):
        return Response(s.UserSerializer(request.user).data)


class RequestViewSet(mixins.CreateModelMixin, mixins.RetrieveModelMixin, mixins.UpdateModelMixin,
                     mixins.ListModelMixin, viewsets.GenericViewSet):
    """Administrative requests. Results are limited to the requests the signed-in user may see."""
    search_fields = ["request_number", "title", "darta_number", "chalani_number"]
    ordering_fields = ["created_at", "updated_at", "request_number", "status"]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return AdministrativeRequest.objects.none()
        user = self.request.user
        qs = visible_requests(user)
        scope = self.request.query_params.get("scope")
        if scope == "mine":
            qs = qs.filter(requester=user)
        elif scope == "action":
            qs = qs.filter(pk__in=action_queue(user).values("pk"))
        return apply_filters(qs, self.request.query_params)

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return s.RequestWriteSerializer
        return s.RequestSerializer

    @extend_schema(parameters=[
        OpenApiParameter("scope", str, description="all | mine | action"),
        OpenApiParameter("q", str), OpenApiParameter("status", str), OpenApiParameter("category", str),
        OpenApiParameter("priority", str), OpenApiParameter("department", int),
        OpenApiParameter("date_from", str, description="YYYY-MM-DD"), OpenApiParameter("date_to", str),
    ])
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    def perform_create(self, serializer):
        user = self.request.user
        if not user.can_create_requests or user.department_id is None:
            raise PermissionDenied("Your account cannot create requests.")
        req = serializer.save(requester=user, department=user.department, status=Status.DRAFT)
        WorkflowLog.objects.create(request=req, action="create", to_status=req.status, actor=user,
                                   from_department=user.department, remarks="Draft created")

    def perform_update(self, serializer):
        if not serializer.instance.can_edit(self.request.user):
            raise PermissionDenied("This request can no longer be edited by you.")
        req = serializer.save()
        WorkflowLog.objects.create(request=req, action="edit", from_status=req.status, to_status=req.status,
                                   actor=self.request.user, remarks="Details updated")

    def create(self, request, *args, **kwargs):
        resp = super().create(request, *args, **kwargs)
        return resp

    @extend_schema(request=s.ActionInputSerializer, responses=s.RequestSerializer)
    @action(detail=True, methods=["post"], url_path="actions")
    def run_action(self, request, pk=None):
        """Run a workflow action (submit, verify, register, forward, approve, ...)."""
        req = self.get_object()
        inp = s.ActionInputSerializer(data=request.data)
        inp.is_valid(raise_exception=True)
        try:
            updated = perform(req, request.user, inp.validated_data["action"], request.data)
        except NotAllowed as exc:
            raise PermissionDenied(str(exc))
        except Invalid as exc:
            raise ValidationError({"detail": str(exc)})
        return Response(s.RequestSerializer(updated, context={"request": request}).data)

    @extend_schema(responses=s.AvailableActionSerializer(many=True))
    @action(detail=True, methods=["get"], url_path="available-actions", pagination_class=None)
    def available(self, request, pk=None):
        req = self.get_object()
        data = [{"key": a["key"], "label": a["label"], "remarks": a["remarks"], "fields": list(a["fields"])}
                for a in available_actions(req, request.user)]
        return Response(data)

    @extend_schema(responses=s.WorkflowLogSerializer(many=True))
    @action(detail=True, methods=["get"], pagination_class=None)
    def timeline(self, request, pk=None):
        req = self.get_object()
        logs = req.logs.select_related("actor", "to_department", "request")
        return Response(s.WorkflowLogSerializer(logs, many=True).data)


class WorkflowLogViewSet(viewsets.ReadOnlyModelViewSet):
    """Audit trail rows for requests you can see."""
    serializer_class = s.WorkflowLogSerializer
    search_fields = ["request__request_number", "remarks"]
    ordering_fields = ["created_at"]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return WorkflowLog.objects.none()
        qs = WorkflowLog.objects.filter(request__in=visible_requests(self.request.user).values("pk"))
        req = self.request.query_params.get("request")
        if req and req.isdigit():
            qs = qs.filter(request_id=int(req))
        return qs.select_related("actor", "to_department", "request").order_by("-created_at", "-id")


class AnnotationViewSet(viewsets.ReadOnlyModelViewSet):
    """Recommendations, tippani and Tok Aadesh on requests you can see."""
    serializer_class = s.AnnotationSerializer

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Annotation.objects.none()
        qs = Annotation.objects.filter(request__in=visible_requests(self.request.user).values("pk"))
        req = self.request.query_params.get("request")
        if req and req.isdigit():
            qs = qs.filter(request_id=int(req))
        return qs.select_related("author")


class DocumentViewSet(mixins.CreateModelMixin, mixins.RetrieveModelMixin, mixins.ListModelMixin,
                      mixins.DestroyModelMixin, viewsets.GenericViewSet):
    """Documents attached to requests (multipart upload). Files are never publicly served."""
    serializer_class = s.DocumentSerializer
    search_fields = ["original_name", "description"]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Document.objects.none()
        qs = Document.objects.filter(request__in=visible_requests(self.request.user).values("pk"))
        req = self.request.query_params.get("request")
        if req and req.isdigit():
            qs = qs.filter(request_id=int(req))
        return qs.select_related("uploaded_by")

    def perform_create(self, serializer):
        req = serializer.validated_data["request"]
        if not visible_requests(self.request.user).filter(pk=req.pk).exists():
            raise PermissionDenied("You cannot see that request.")
        if not can_upload(self.request.user, req):
            raise PermissionDenied("You cannot upload documents to this request at its current stage.")
        serializer.save()

    def perform_destroy(self, instance):
        if not can_delete(self.request.user, instance):
            raise PermissionDenied("You cannot delete this document.")
        instance.file.delete(save=False)
        instance.delete()

    @extend_schema(responses={(200, "application/octet-stream"): OpenApiTypes.BINARY})
    @action(detail=True, methods=["get"])
    def download(self, request, pk=None):
        doc = self.get_object()
        try:
            handle = doc.file.open("rb")
        except FileNotFoundError:
            raise Http404
        return FileResponse(handle, as_attachment=True, filename=doc.original_name,
                            content_type=doc.content_type or "application/octet-stream")


class NotificationViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    """Your own notifications."""
    serializer_class = s.NotificationSerializer

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Notification.objects.none()
        qs = Notification.objects.filter(recipient=self.request.user)
        if self.request.query_params.get("unread") in ("1", "true"):
            qs = qs.filter(is_read=False)
        return qs

    @extend_schema(request=None, responses=s.NotificationSerializer)
    @action(detail=True, methods=["post"], url_path="mark-read")
    def mark_read(self, request, pk=None):
        n = self.get_object()
        n.is_read = True
        n.save(update_fields=["is_read"])
        return Response(s.NotificationSerializer(n).data)

    @extend_schema(request=None, responses=OpenApiTypes.OBJECT)
    @action(detail=False, methods=["post"], url_path="mark-all-read")
    def mark_all_read(self, request):
        updated = Notification.objects.filter(recipient=request.user, is_read=False).update(is_read=True)
        return Response({"marked": updated})

    @extend_schema(responses=OpenApiTypes.OBJECT)
    @action(detail=False, methods=["get"], url_path="unread-count")
    def unread_count(self, request):
        return Response({"unread": self.get_queryset().filter(is_read=False).count()})
