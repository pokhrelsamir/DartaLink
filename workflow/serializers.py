from rest_framework import serializers

from .models import Document, DartaEntry


class DartaEntrySerializer(serializers.ModelSerializer):
    # Document fields received from the Darta form
    subject = serializers.CharField(
        source="document.subject",
        max_length=255
    )

    description = serializers.CharField(
        source="document.description",
        required=False,
        allow_blank=True,
        allow_null=True
    )

    class Meta:
        model = DartaEntry
        fields = [
            "id",
            "darta_number",
            "sender_organization",
            "reference_number",
            "received_date",
            "urgency",
            "receiving_branch",
            "subject",
            "description",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "created_at",
        ]

    def create(self, validated_data):
        document_data = validated_data.pop("document")

        request = self.context.get("request")
        user = request.user if request else None

        if not user or not user.is_authenticated:
            raise serializers.ValidationError(
                "Authenticated user is required to create a Darta entry."
            )

        # Generate a unique document tracking number
        tracking_number = f"DL-{validated_data['darta_number']}"

        document = Document.objects.create(
            tracking_number=tracking_number,
            subject=document_data["subject"],
            description=document_data.get("description"),
            created_by=user
        )

        darta_entry = DartaEntry.objects.create(
            document=document,
            **validated_data
        )

        return darta_entry