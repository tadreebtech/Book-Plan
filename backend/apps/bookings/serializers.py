from django.utils import timezone
from rest_framework import serializers

from apps.bookings.models import Booking, BookingStatus, Resource


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
        if obj.status == BookingStatus.CANCELLED:
            return BookingStatus.CANCELLED
        if obj.status == BookingStatus.COMPLETED or obj.end_at <= timezone.now():
            return BookingStatus.COMPLETED
        return BookingStatus.CONFIRMED
