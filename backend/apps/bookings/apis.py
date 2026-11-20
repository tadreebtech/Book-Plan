import re

from rest_framework import serializers
from rest_framework.exceptions import NotFound
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import IsAdminRole
from apps.bookings.models import Resource
from apps.bookings.services import resource_approve, resource_hide, resource_reject


class AdminListingModerationApi(APIView):
    """Класс, задающий права доступа и формат ответа для операций модерации"""

    permission_classes = [IsAuthenticated, IsAdminRole]

    class OutputSerializer(serializers.ModelSerializer):
        """Класс, представляющий статус объявления и данные о последнем решении"""

        class Meta:
            """Класс, задающий поля объявления после модерации"""

            model = Resource
            fields = ("id", "moderation_status", "rejection_reason", "moderated_at", "moderated_by")
            read_only_fields = fields

    @staticmethod
    def parse_resource_id(value: str) -> int:
        """Метод, проверяющий идентификатор объявления из адреса запроса"""

        if not re.fullmatch(r"[0-9]{1,19}", value):
            raise NotFound()

        resource_id = int(value)
        if not 1 <= resource_id <= 2**63 - 1:
            raise NotFound()
        return resource_id


class AdminListingApproveApi(AdminListingModerationApi):
    """Класс, одобряющий выбранное объявление по запросу администратора"""

    def post(self, request: Request, resource_id: str) -> Response:
        """Метод, возвращающий объявление после одобрения"""

        resource = resource_approve(
            actor=request.user, resource_id=self.parse_resource_id(resource_id)
        )
        return Response(self.OutputSerializer(resource).data)


class AdminListingRejectApi(AdminListingModerationApi):
    """Класс, отклоняющий выбранное объявление по запросу администратора"""

    class InputSerializer(serializers.Serializer):
        """Класс, проверяющий обязательную текстовую причину отклонения"""

        rejection_reason = serializers.CharField()

        def validate_rejection_reason(self, value: str) -> str:
            """Метод, проверяющий, что причина передана строкой"""

            if not isinstance(self.initial_data["rejection_reason"], str):
                raise serializers.ValidationError("Expected a string.")
            return value

    def post(self, request: Request, resource_id: str) -> Response:
        """Метод, проверяющий причину и возвращающий объявление после отклонения"""

        pk = self.parse_resource_id(resource_id)
        serializer = self.InputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        resource = resource_reject(actor=request.user, resource_id=pk, **serializer.validated_data)
        return Response(self.OutputSerializer(resource).data)


class AdminListingHideApi(AdminListingModerationApi):
    """Класс, скрывающий выбранное объявление по запросу администратора"""

    def post(self, request: Request, resource_id: str) -> Response:
        """Метод, возвращающий объявление после скрытия"""

        resource = resource_hide(
            actor=request.user, resource_id=self.parse_resource_id(resource_id)
        )
        return Response(self.OutputSerializer(resource).data)
