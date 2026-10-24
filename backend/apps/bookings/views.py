from django.http import Http404
from django.utils.decorators import method_decorator
from django.utils.translation import override
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import APIException, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.bookings.serializers import BookingCreateSerializer, BookingReadSerializer
from apps.bookings.services import cancel_booking, create_booking, list_user_bookings


@method_decorator(override("en"), name="dispatch")
class BookingViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    serializer_class = BookingReadSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return list_user_bookings(user=self.request.user)

    def get_serializer_class(self):
        if self.action == "create":
            return BookingCreateSerializer
        return BookingReadSerializer

    def create(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        booking = create_booking(user=request.user, **serializer.validated_data)
        return Response(
            BookingReadSerializer(booking).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["post"], url_path="cancel")
    def cancel(self, request, pk=None):
        booking = cancel_booking(user=request.user, booking_id=pk)
        return Response(BookingReadSerializer(booking).data)

    def handle_exception(self, exc):
        response = super().handle_exception(exc)
        if response is None:
            return None

        raw = response.data
        if isinstance(raw, dict) and "detail" in raw:
            message = str(raw["detail"])
            details = {}
        elif isinstance(raw, (dict, list)):
            message = "Invalid request data."
            details = raw
        else:
            message = str(raw)
            details = {}

        if isinstance(exc, ValidationError):
            code = "validation_error"
        elif isinstance(exc, Http404):
            code = "not_found"
        elif isinstance(exc, APIException):
            codes = exc.get_codes()
            code = codes if isinstance(codes, str) else "api_error"
        else:
            code = "error"

        response.data = {"error": {"code": code, "message": message, "details": details}}
        return response
