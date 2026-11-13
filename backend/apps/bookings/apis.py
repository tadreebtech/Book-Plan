from rest_framework import serializers
from rest_framework.exceptions import NotFound
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import User
from apps.accounts.permissions import IsAdminRole
from apps.accounts.selectors import user_get_display_name
from apps.bookings.models import BookingStatus, ResourceKind
from apps.bookings.selectors import booking_get, booking_list


class BookingListApi(APIView):
    """Класс, возвращающий администратору список всех броней платформы только для чтения"""

    permission_classes = [IsAuthenticated, IsAdminRole]

    class InputSerializer(serializers.Serializer):
        """Класс, проверяющий параметры фильтрации, сортировки и пагинации броней"""

        page = serializers.IntegerField(min_value=1, default=1)
        page_size = serializers.IntegerField(min_value=1, max_value=100, default=20)
        status = serializers.ChoiceField(choices=BookingStatus.values, required=False)
        date_from = serializers.DateField(required=False)
        date_to = serializers.DateField(required=False)
        category = serializers.ChoiceField(choices=ResourceKind.values, required=False)
        provider = serializers.IntegerField(min_value=1, required=False)
        client = serializers.IntegerField(min_value=1, required=False)
        ordering = serializers.ChoiceField(
            choices=("-created_at", "created_at", "-start_at", "start_at"),
            default="-created_at",
        )

        def validate(self, attrs: dict) -> dict:
            """Метод, проверяющий, что начало отрезка дат не позже его конца"""

            date_from = attrs.get("date_from")
            date_to = attrs.get("date_to")
            if date_from is not None and date_to is not None and date_from > date_to:
                raise serializers.ValidationError(
                    {"date_to": ["date_to must not be earlier than date_from."]}
                )
            return attrs

    class OutputSerializer(serializers.Serializer):
        """Класс, представляющий основные данные брони в списке"""

        class ClientSerializer(serializers.Serializer):
            """Класс, представляющий клиента, оформившего бронь"""

            id = serializers.IntegerField()
            email = serializers.EmailField()
            name = serializers.SerializerMethodField()

            def get_name(self, user: User) -> str:
                """Метод, возвращающий полное имя клиента или его логин"""

                return user_get_display_name(user=user)

        class ResourceSerializer(serializers.Serializer):
            """Класс, представляющий забронированный ресурс"""

            id = serializers.IntegerField()
            name = serializers.CharField()
            kind = serializers.CharField()

        class PeriodSerializer(serializers.Serializer):
            """Класс, представляющий начало и конец брони"""

            start_at = serializers.DateTimeField()
            end_at = serializers.DateTimeField()

        id = serializers.IntegerField()
        client = ClientSerializer(source="user")
        resource = ResourceSerializer()
        period = PeriodSerializer(source="*")
        status = serializers.CharField()
        created_at = serializers.DateTimeField()

    def get(self, request: Request) -> Response:
        """Метод, возвращающий страницу броней с общим количеством записей"""

        serializer = self.InputSerializer(data=request.query_params.dict())
        serializer.is_valid(raise_exception=True)
        params = serializer.validated_data

        bookings = booking_list(
            status=params.get("status"),
            date_from=params.get("date_from"),
            date_to=params.get("date_to"),
            category=params.get("category"),
            provider_id=params.get("provider"),
            client_id=params.get("client"),
            ordering=params["ordering"],
        )
        count = bookings.count()
        page = params["page"]
        page_size = params["page_size"]
        start = (page - 1) * page_size
        results = (
            self.OutputSerializer(bookings[start : start + page_size], many=True).data
            if start < count
            else []
        )

        return Response({"count": count, "page": page, "page_size": page_size, "results": results})


class BookingDetailApi(APIView):
    """Класс, возвращающий администратору карточку брони по идентификатору"""

    permission_classes = [IsAuthenticated, IsAdminRole]

    class InputSerializer(serializers.Serializer):
        """Класс, проверяющий идентификатор брони из адреса запроса"""

        id = serializers.IntegerField(min_value=1)

    class OutputSerializer(serializers.Serializer):
        """Класс, представляющий расширенные данные брони в карточке"""

        class PersonSerializer(serializers.Serializer):
            """Класс, представляющий клиента или менеджера ресурса"""

            id = serializers.IntegerField()
            email = serializers.EmailField()
            name = serializers.SerializerMethodField()

            def get_name(self, user: User) -> str:
                """Метод, возвращающий полное имя пользователя или его логин"""

                return user_get_display_name(user=user)

        class ResourceSerializer(serializers.Serializer):
            """Класс, представляющий забронированный ресурс"""

            id = serializers.IntegerField()
            name = serializers.CharField()
            kind = serializers.CharField()
            capacity = serializers.IntegerField()
            is_active = serializers.BooleanField()

        class PeriodSerializer(serializers.Serializer):
            """Класс, представляющий начало и конец брони"""

            start_at = serializers.DateTimeField()
            end_at = serializers.DateTimeField()

        id = serializers.IntegerField()
        client = PersonSerializer(source="user")
        resource = ResourceSerializer()
        provider = PersonSerializer(source="resource.manager", allow_null=True)
        period = PeriodSerializer(source="*")
        guests = serializers.IntegerField()
        status = serializers.CharField()
        created_at = serializers.DateTimeField()
        updated_at = serializers.DateTimeField()

    def get(self, request: Request, booking_id: str) -> Response:
        """Метод, возвращающий расширенные данные выбранной брони"""

        serializer = self.InputSerializer(data={"id": booking_id})
        serializer.is_valid(raise_exception=True)
        booking = booking_get(booking_id=serializer.validated_data["id"])
        if booking is None:
            raise NotFound()
        return Response(self.OutputSerializer(booking).data)
