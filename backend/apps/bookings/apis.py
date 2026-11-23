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
from apps.common.pagination import MAX_DB_ID, PaginationInputSerializer, paginated_response_data


class BookingPersonSerializer(serializers.Serializer):
    """Класс, представляющий клиента брони или менеджера ресурса"""

    id = serializers.IntegerField()
    email = serializers.EmailField()
    name = serializers.SerializerMethodField()

    def get_name(self, user: User) -> str:
        """Метод, возвращающий полное имя пользователя или его логин"""

        return user_get_display_name(user=user)


class BookingResourceSerializer(serializers.Serializer):
    """Класс, представляющий забронированный ресурс"""

    id = serializers.IntegerField()
    name = serializers.CharField()
    kind = serializers.CharField()


class BookingPeriodSerializer(serializers.Serializer):
    """Класс, представляющий начало и конец брони"""

    start_at = serializers.DateTimeField()
    end_at = serializers.DateTimeField()


class BookingListApi(APIView):
    """Класс, возвращающий администратору список всех броней платформы только для чтения"""

    permission_classes = [IsAuthenticated, IsAdminRole]

    class InputSerializer(PaginationInputSerializer):
        """Класс, проверяющий параметры фильтрации, сортировки и пагинации броней"""

        status = serializers.ChoiceField(choices=BookingStatus.values, required=False)
        date_from = serializers.DateField(required=False)
        date_to = serializers.DateField(required=False)
        category = serializers.ChoiceField(choices=ResourceKind.values, required=False)
        provider = serializers.IntegerField(min_value=1, max_value=MAX_DB_ID, required=False)
        client = serializers.IntegerField(min_value=1, max_value=MAX_DB_ID, required=False)
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

        id = serializers.IntegerField()
        client = BookingPersonSerializer(source="user")
        resource = BookingResourceSerializer()
        period = BookingPeriodSerializer(source="*")
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
        return Response(
            paginated_response_data(
                queryset=bookings,
                serializer_class=self.OutputSerializer,
                page=params["page"],
                page_size=params["page_size"],
            )
        )


class BookingDetailApi(APIView):
    """Класс, возвращающий администратору карточку брони по идентификатору"""

    permission_classes = [IsAuthenticated, IsAdminRole]

    class InputSerializer(serializers.Serializer):
        """Класс, проверяющий идентификатор брони из адреса запроса"""

        id = serializers.IntegerField(min_value=1, max_value=MAX_DB_ID)

    class OutputSerializer(serializers.Serializer):
        """Класс, представляющий расширенные данные брони в карточке"""

        class ResourceSerializer(BookingResourceSerializer):
            """Класс, дополняющий данные ресурса вместимостью и доступностью"""

            capacity = serializers.IntegerField()
            is_active = serializers.BooleanField()

        id = serializers.IntegerField()
        client = BookingPersonSerializer(source="user")
        resource = ResourceSerializer()
        provider = BookingPersonSerializer(source="resource.manager", allow_null=True)
        period = BookingPeriodSerializer(source="*")
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
