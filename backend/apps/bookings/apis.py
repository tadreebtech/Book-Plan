from rest_framework import serializers, status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.bookings.models import Booking, Resource
from apps.bookings.selectors import booking_get, booking_list
from apps.bookings.services import booking_cancel, booking_create


class BookingDetailApi(APIView):
    """Класс, отдающий одну бронь текущего пользователя по ее номеру"""

    class OutputSerializer(serializers.ModelSerializer):
        """Класс, описывающий поля брони, которые уходят в ответ API"""

        resource_name = serializers.CharField(source="resource.name")
        resource_kind = serializers.CharField(source="resource.kind")
        status = serializers.CharField(source="effective_status")

        class Meta:
            """Класс, перечисляющий поля брони в ответе API"""

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

    def get(self, request: Request, booking_id: int) -> Response:
        """Метод, возвращающий бронь пользователя или ошибку NOT_FOUND"""
        booking = booking_get(user=request.user, booking_id=booking_id)
        return Response(self.OutputSerializer(booking).data)


class BookingListApi(APIView):
    """Класс, отдающий список текущих и прошлых броней пользователя"""

    def get(self, request: Request) -> Response:
        """Метод, возвращающий все брони пользователя от поздних к ранним"""
        bookings = booking_list(user=request.user)
        return Response(BookingDetailApi.OutputSerializer(bookings, many=True).data)


class BookingCreateApi(APIView):
    """Класс, принимающий запрос на создание брони ресурса"""

    class InputSerializer(serializers.Serializer):
        """Класс, проверяющий форму данных для новой брони: ресурс, время и число гостей"""

        resource = serializers.PrimaryKeyRelatedField(queryset=Resource.objects.all())
        start_at = serializers.DateTimeField()
        end_at = serializers.DateTimeField()
        guests = serializers.IntegerField(min_value=1)

    def post(self, request: Request) -> Response:
        """Метод, создающий бронь и возвращающий ее с кодом 201"""
        serializer = self.InputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        booking = booking_create(user=request.user, **serializer.validated_data)
        return Response(
            BookingDetailApi.OutputSerializer(booking).data, status=status.HTTP_201_CREATED
        )


class BookingListCreateApi(APIView):
    """Класс, направляющий GET-запрос к списку броней, а POST-запрос к созданию брони"""

    def get(self, request: Request) -> Response:
        """Метод, передающий запрос списку броней"""
        return BookingListApi.as_view()(request._request)

    def post(self, request: Request) -> Response:
        """Метод, передающий запрос созданию брони"""
        return BookingCreateApi.as_view()(request._request)


class BookingCancelApi(APIView):
    """Класс, принимающий запрос на отмену брони пользователя"""

    def post(self, request: Request, booking_id: int) -> Response:
        """Метод, отменяющий бронь и возвращающий ее с новым статусом"""
        booking = booking_cancel(user=request.user, booking_id=booking_id)
        return Response(BookingDetailApi.OutputSerializer(booking).data)
