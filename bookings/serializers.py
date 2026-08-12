from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils import timezone
from rest_framework import serializers

from .models import BookingRequest, LSAProfile, Parent, Payment, Skill


class ParentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Parent
        fields = [
            "id",
            "full_name",
            "email",
            "phone_number",
            "child_name",
            "child_age",
            "notes",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class SkillSerializer(serializers.ModelSerializer):
    class Meta:
        model = Skill
        fields = ["id", "name"]
        read_only_fields = ["id"]


class LSAProfileSerializer(serializers.ModelSerializer):
    skills = SkillSerializer(many=True, read_only=True)
    skill_ids = serializers.PrimaryKeyRelatedField(
        queryset=Skill.objects.all(),
        source="skills",
        many=True,
        write_only=True,
        required=False,
    )

    class Meta:
        model = LSAProfile
        fields = [
            "id",
            "full_name",
            "email",
            "phone_number",
            "bio",
            "hourly_rate",
            "years_of_experience",
            "availability_status",
            "skills",
            "skill_ids",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class BookingRequestSerializer(serializers.ModelSerializer):
    parent = ParentSerializer(read_only=True)
    lsa = LSAProfileSerializer(read_only=True)
    parent_id = serializers.PrimaryKeyRelatedField(
        queryset=Parent.objects.all(),
        source="parent",
        write_only=True,
    )
    lsa_id = serializers.PrimaryKeyRelatedField(
        queryset=LSAProfile.objects.all(),
        source="lsa",
        write_only=True,
    )

    class Meta:
        model = BookingRequest
        fields = [
            "id",
            "parent",
            "lsa",
            "parent_id",
            "lsa_id",
            "start_time",
            "end_time",
            "status",
            "special_requirements",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "status", "created_at", "updated_at"]

    def validate(self, attrs):
        start_time = attrs.get("start_time")
        end_time = attrs.get("end_time")
        lsa = attrs.get("lsa")

        if start_time and start_time < timezone.now():
            raise serializers.ValidationError(
                {"start_time": "Booking start time cannot be in the past."}
            )

        if start_time and end_time and end_time <= start_time:
            raise serializers.ValidationError(
                {"end_time": "Booking end time must be after start time."}
            )

        if lsa and lsa.availability_status != LSAProfile.AvailabilityStatus.AVAILABLE:
            raise serializers.ValidationError(
                {"lsa_id": "Selected LSA is not currently available."}
            )

        return attrs

    def create(self, validated_data):
        booking = BookingRequest(**validated_data)

        try:
            booking.full_clean()
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.message_dict if hasattr(exc, "message_dict") else exc.messages)

        booking.save()
        return booking


class PaymentWebhookSerializer(serializers.Serializer):
    provider_reference = serializers.CharField(max_length=120)
    status = serializers.ChoiceField(
        choices=[
            Payment.PaymentStatus.SUCCESS,
            Payment.PaymentStatus.FAILED,
        ]
    )
    raw_payload = serializers.JSONField(required=False)

    def validate_provider_reference(self, value):
        if not Payment.objects.filter(provider_reference=value).exists():
            raise serializers.ValidationError(
                "No payment exists for this provider reference."
            )
        return value
