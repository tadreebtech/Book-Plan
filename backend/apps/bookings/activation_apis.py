from django.utils import timezone
from rest_framework import serializers
from rest_framework.exceptions import NotFound
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import IsAdminRole
from apps.bookings.models import BookingStatus, Resource
from apps.bookings.services import resource_activate, resource_deactivate

MAX_DB_ID = 2**63 - 1


class AdminListingActivationApi(APIView):
    """Класс, задающий права доступа, проверку идентификатора и ответ для смены активности"""

    permission_classes = [IsAuthenticated, IsAdminRole]
    service = None

    class InputSerializer(serializers.Serializer):
        """Класс, проверяющий идентификатор ресурса из адреса запроса"""

        id = serializers.IntegerField(min_value=1, max_value=MAX_DB_ID)

    class OutputSerializer(serializers.Serializer):
        """Класс, представляющий активность ресурса и число действующих броней"""

        id = serializers.IntegerField()
        is_active = serializers.BooleanField()
        upcoming_bookings = serializers.SerializerMethodField()

        def get_upcoming_bookings(self, resource: Resource) -> int:
            """Метод, считающий подтверждённые брони, которые ещё не закончились"""

            return resource.bookings.filter(
                status=BookingStatus.CONFIRMED, end_at__gt=timezone.now()
            ).count()

    def post(self, request: Request, resource_id: str) -> Response:
        """Метод, меняющий активность ресурса и возвращающий его текущее состояние"""

        serializer = self.InputSerializer(data={"id": resource_id})
        serializer.is_valid(raise_exception=True)
        try:
            resource = self.service(actor=request.user, resource_id=serializer.validated_data["id"])
        except Resource.DoesNotExist as exc:
            raise NotFound() from exc
        return Response(self.OutputSerializer(resource).data)


class AdminListingActivateApi(AdminListingActivationApi):
    """Класс, активирующий ресурс по запросу администратора"""

    service = staticmethod(resource_activate)


class AdminListingDeactivateApi(AdminListingActivationApi):
    """Класс, деактивирующий ресурс без отмены существующих броней"""

    service = staticmethod(resource_deactivate)
