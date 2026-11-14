from django.utils import timezone
from rest_framework import serializers

from apps.bookings.models import Booking, BookingStatus, ModerationStatus, Resource, ResourceKind


class BookingCreateSerializer(serializers.Serializer):
    resource = serializers.PrimaryKeyRelatedField(queryset=Resource.objects.all())
    start_at = serializers.DateTimeField()
    end_at = serializers.DateTimeField()
    guests = serializers.IntegerField(min_value=1)

    def validate(self, attrs):
        if attrs["end_at"] <= attrs["start_at"]:
            raise serializers.ValidationError({"end_at": ["End time must be after start time."]})
        return attrs


class BookingReadSerializer(serializers.ModelSerializer):
    resource_name = serializers.CharField(source="resource.name", read_only=True)
    resource_kind = serializers.CharField(source="resource.kind", read_only=True)
    status = serializers.SerializerMethodField()

    class Meta:
        model = Booking
        fields = (
            "id",
            "resource",
            "resource_name",
            "resource_kind",
            "start_at",
            "end_at",
            "guests",
            "status",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields

    def get_status(self, obj: Booking) -> str:
        # Effective status is derived from the end time, without changing the stored status.
        if obj.status == BookingStatus.CANCELLED:
            return BookingStatus.CANCELLED
        if obj.status == BookingStatus.COMPLETED or obj.end_at <= timezone.now():
            return BookingStatus.COMPLETED
        return BookingStatus.CONFIRMED


class AdminListingQuerySerializer(serializers.Serializer):
    moderation_status = serializers.ChoiceField(choices=ModerationStatus.choices, required=False)
    category = serializers.ChoiceField(choices=ResourceKind.choices, required=False)
    provider = serializers.IntegerField(min_value=1, max_value=2**63 - 1, required=False)
    search = serializers.CharField(required=False, allow_blank=True, max_length=255, default="")
    page = serializers.IntegerField(min_value=1, default=1)
    page_size = serializers.IntegerField(min_value=1, max_value=100, default=20)


class AdminListingReadSerializer(serializers.ModelSerializer):
    title = serializers.CharField(source="name", read_only=True)
    category = serializers.CharField(source="kind", read_only=True)
    provider = serializers.IntegerField(source="manager_id", read_only=True, allow_null=True)

    class Meta:
        model = Resource
        fields = ("id", "title", "category", "provider", "moderation_status", "created_at")
        read_only_fields = fields
