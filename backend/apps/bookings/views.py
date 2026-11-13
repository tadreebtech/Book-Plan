from django.http import Http404
from django.utils.decorators import method_decorator
from django.utils.translation import override
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import APIException, NotFound, ValidationError
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import IsAdminRole
from apps.bookings.models import Resource
from apps.bookings.serializers import (
    AdminListingQuerySerializer,
    AdminListingReadSerializer,
    BookingCreateSerializer,
    BookingReadSerializer,
)
from apps.bookings.services import cancel_booking, create_booking, list_user_bookings


@method_decorator(override("en"), name="dispatch")
class BookingViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    serializer_class = BookingReadSerializer

    @staticmethod
    def _parse_booking_id(value):
        try:
            return int(value)
        except (TypeError, ValueError) as exc:
            raise NotFound("Booking not found.") from exc

    def get_object(self):
        self._parse_booking_id(self.kwargs.get(self.lookup_url_kwarg or self.lookup_field))
        return super().get_object()

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
        booking = cancel_booking(user=request.user, booking_id=self._parse_booking_id(pk))
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
            code = "VALIDATION_ERROR"
        elif isinstance(exc, Http404):
            code = "NOT_FOUND"
        elif isinstance(exc, APIException):
            codes = exc.get_codes()
            code = codes.upper() if isinstance(codes, str) else "API_ERROR"
        else:
            code = "ERROR"

        response.data = {"error": {"code": code, "message": message, "details": details}}
        return response


class AdminListingListApi(APIView):
    permission_classes = [IsAdminRole]

    def get(self, request: Request) -> Response:
        query = AdminListingQuerySerializer(data=request.query_params.dict())
        query.is_valid(raise_exception=True)
        params = query.validated_data

        listings = Resource.objects.order_by("-created_at", "-pk")
        if "moderation_status" in params:
            listings = listings.filter(moderation_status=params["moderation_status"])
        if "category" in params:
            listings = listings.filter(kind=params["category"])
        if "provider" in params:
            listings = listings.filter(manager_id=params["provider"])
        if params["search"]:
            listings = listings.filter(name__icontains=params["search"])

        count = listings.count()
        page = params["page"]
        page_size = params["page_size"]
        start = (page - 1) * page_size
        results = (
            AdminListingReadSerializer(listings[start : start + page_size], many=True).data
            if start < count
            else []
        )
        return Response({"count": count, "page": page, "page_size": page_size, "results": results})
