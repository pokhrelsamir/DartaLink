from django.contrib.auth import password_validation
from rest_framework import serializers

from accounts.models import ROLE_DEPT_CODE, Department, Role, StaffProfile, User
from documents.models import Document
from documents.validators import validate_upload
from notifications.models import Notification
from requests_app.models import AdministrativeRequest
from workflow.models import Annotation, WorkflowLog


class DepartmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Department
        fields = ["id", "name", "name_np", "code", "description", "is_authority", "is_registry", "is_active"]

    def validate_code(self, value):
        return value.strip().upper()


class StaffProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = StaffProfile
        fields = ["designation", "phone", "office_location", "employment_type", "joined_on",
                  "emergency_contact", "address"]


class UserSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(source="display_name", read_only=True)
    role_display = serializers.CharField(source="get_role_display", read_only=True)
    department_name = serializers.CharField(source="department.name", read_only=True, default=None)

    class Meta:
        model = User
        fields = ["id", "staff_id", "username", "full_name", "role", "role_display", "department",
                  "department_name", "is_active"]
        read_only_fields = fields


class UserWriteSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False, style={"input_type": "password"})
    profile = StaffProfileSerializer(required=False)

    class Meta:
        model = User
        fields = ["id", "staff_id", "username", "first_name", "last_name", "email", "role", "department",
                  "is_active", "password", "profile"]
        read_only_fields = ["id", "staff_id"]

    def validate(self, attrs):
        role = attrs.get("role", getattr(self.instance, "role", Role.STAFF))
        dept = attrs.get("department", getattr(self.instance, "department", None))
        needed = ROLE_DEPT_CODE.get(role)
        if needed and (dept is None or dept.code != needed):
            raise serializers.ValidationError({"department": f"{role} must belong to department {needed}."})
        if role != Role.SYSADMIN and dept is None:
            raise serializers.ValidationError({"department": "A department is required for this role."})
        if not self.instance and not attrs.get("password"):
            raise serializers.ValidationError({"password": "Password is required."})
        if attrs.get("password"):
            password_validation.validate_password(attrs["password"])
        return attrs

    def _save(self, instance, validated):
        profile = validated.pop("profile", None)
        password = validated.pop("password", None)
        for k, v in validated.items():
            setattr(instance, k, v)
        if password:
            instance.set_password(password)
        instance.save()
        if profile:
            StaffProfile.objects.update_or_create(user=instance, defaults=profile)
        return instance

    def create(self, validated):
        return self._save(User(), validated)

    def update(self, instance, validated):
        return self._save(instance, validated)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data.pop("password", None)
        return data


class RequestSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    category_display = serializers.CharField(source="get_category_display", read_only=True)
    priority_display = serializers.CharField(source="get_priority_display", read_only=True)
    requester_name = serializers.CharField(source="requester.display_name", read_only=True)
    requester_staff_id = serializers.CharField(source="requester.staff_id", read_only=True)
    department_name = serializers.CharField(source="department.name", read_only=True)
    current_department_name = serializers.CharField(source="current_department.name", read_only=True, default=None)
    editable = serializers.SerializerMethodField()

    class Meta:
        model = AdministrativeRequest
        fields = ["id", "request_number", "title", "category", "category_display", "priority", "priority_display",
                  "description", "requested_amount", "required_by", "status", "status_display", "requester",
                  "requester_name", "requester_staff_id", "department", "department_name", "current_department",
                  "current_department_name", "darta_number", "darta_date", "chalani_number", "chalani_date",
                  "dispatched_to", "approved_at", "decision_remarks", "created_at", "updated_at",
                  "submitted_at", "completed_at", "editable"]
        read_only_fields = ["id", "request_number", "status", "requester", "department", "current_department",
                            "darta_number", "darta_date", "chalani_number", "chalani_date", "dispatched_to",
                            "approved_at", "decision_remarks", "created_at", "updated_at", "submitted_at",
                            "completed_at"]

    def get_editable(self, obj) -> bool:
        request = self.context.get("request")
        return bool(request and obj.can_edit(request.user))


class RequestWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = AdministrativeRequest
        fields = ["id", "request_number", "title", "category", "priority", "description",
                  "requested_amount", "required_by", "status"]
        read_only_fields = ["id", "request_number", "status"]

    def validate_requested_amount(self, value):
        if value is not None and value < 0:
            raise serializers.ValidationError("Amount cannot be negative.")
        return value


class ActionInputSerializer(serializers.Serializer):
    action = serializers.CharField()
    remarks = serializers.CharField(required=False, allow_blank=True)
    to_department = serializers.IntegerField(required=False)
    dispatched_to = serializers.CharField(required=False, allow_blank=True)


class AvailableActionSerializer(serializers.Serializer):
    key = serializers.CharField()
    label = serializers.CharField()
    remarks = serializers.CharField()
    fields = serializers.ListField(child=serializers.CharField())


class WorkflowLogSerializer(serializers.ModelSerializer):
    actor_name = serializers.CharField(source="actor.display_name", read_only=True, default=None)
    actor_staff_id = serializers.CharField(source="actor.staff_id", read_only=True, default=None)
    request_number = serializers.CharField(source="request.request_number", read_only=True)
    to_department_name = serializers.CharField(source="to_department.name", read_only=True, default=None)

    class Meta:
        model = WorkflowLog
        fields = ["id", "request", "request_number", "action", "from_status", "to_status", "actor",
                  "actor_name", "actor_staff_id", "to_department", "to_department_name", "remarks", "created_at"]
        read_only_fields = fields


class AnnotationSerializer(serializers.ModelSerializer):
    author_name = serializers.CharField(source="author.display_name", read_only=True, default=None)
    kind_display = serializers.CharField(source="get_kind_display", read_only=True)

    class Meta:
        model = Annotation
        fields = ["id", "request", "kind", "kind_display", "text", "author", "author_name", "department", "created_at"]
        read_only_fields = fields


class DocumentSerializer(serializers.ModelSerializer):
    file = serializers.FileField(write_only=True)
    uploaded_by_name = serializers.CharField(source="uploaded_by.display_name", read_only=True, default=None)
    download_url = serializers.SerializerMethodField()

    class Meta:
        model = Document
        fields = ["id", "request", "file", "original_name", "kind", "description", "size", "content_type",
                  "uploaded_by", "uploaded_by_name", "uploaded_at", "download_url"]
        read_only_fields = ["id", "original_name", "size", "content_type", "uploaded_by", "uploaded_at"]

    def get_download_url(self, obj) -> str:
        return f"/documents/{obj.pk}/download/"

    def validate_file(self, f):
        from django.core.exceptions import ValidationError as DjangoValidationError
        try:
            validate_upload(f)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.messages)
        return f

    def create(self, validated):
        f = validated["file"]
        return Document.objects.create(
            request=validated["request"], file=f, original_name=f.name[:255],
            kind=validated.get("kind", Document.Kind.SUPPORTING), description=validated.get("description", ""),
            size=f.size, content_type=(getattr(f, "content_type", "") or "")[:100],
            uploaded_by=self.context["request"].user,
        )


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ["id", "request", "title", "message", "level", "is_read", "created_at"]
        read_only_fields = ["id", "request", "title", "message", "level", "created_at"]
