from rest_framework import serializers
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import Role, User
from apps.accounts.permissions import IsAdminRole
from apps.accounts.selectors import user_list


class UserListApi(APIView):
    """Класс, возвращающий администратору список пользователей платформы"""

    permission_classes = [IsAuthenticated, IsAdminRole]

    class InputSerializer(serializers.Serializer):
        """Класс, проверяющий параметры поиска, фильтрации и пагинации пользователей"""

        page = serializers.IntegerField(min_value=1, default=1)
        page_size = serializers.IntegerField(min_value=1, max_value=100, default=20)
        search = serializers.CharField(required=False, allow_blank=True, max_length=150, default="")
        role = serializers.CharField(required=False)
        is_active = serializers.BooleanField(required=False)
        ordering = serializers.ChoiceField(
            choices=("-created_at", "created_at", "email", "-email"),
            default="-created_at",
        )

        def validate_role(self, value: str) -> str:
            """Метод, приводящий название роли к значению, используемому в базе данных"""

            role = value.upper()
            if role == "PROVIDER":
                role = Role.MANAGER
            if role not in Role.values:
                raise serializers.ValidationError("Неизвестная роль пользователя.")
            return role

    class OutputSerializer(serializers.Serializer):
        """Класс, представляющий базовые данные пользователя в ответе API"""

        id = serializers.IntegerField()
        email = serializers.EmailField()
        name = serializers.SerializerMethodField()
        role = serializers.CharField()
        is_active = serializers.BooleanField()
        created_at = serializers.DateTimeField()

        def get_name(self, user: User) -> str:
            """Метод, возвращающий полное имя или логин, если имя не заполнено"""

            return user.get_full_name().strip() or user.username

    def get(self, request: Request) -> Response:
        """Метод, возвращающий страницу пользователей с общим количеством записей"""

        serializer = self.InputSerializer(data=request.query_params.dict())
        serializer.is_valid(raise_exception=True)
        params = serializer.validated_data

        users = user_list(
            search=params["search"],
            role=params.get("role"),
            is_active=params.get("is_active"),
            ordering=params["ordering"],
        )
        count = users.count()
        page = params["page"]
        page_size = params["page_size"]
        start = (page - 1) * page_size
        results = (
            self.OutputSerializer(users[start : start + page_size], many=True).data
            if start < count
            else []
        )

        return Response({"count": count, "page": page, "page_size": page_size, "results": results})
