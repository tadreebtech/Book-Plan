from rest_framework.permissions import BasePermission
from rest_framework.request import Request

from apps.accounts.models import Role


class IsAdminRole(BasePermission):
    """Класс, разрешающий доступ активному незаблокированному администратору"""

    def has_permission(self, request: Request, view: object) -> bool:
        """Метод, проверяющий роль и состояние пользователя для защищённого запроса"""

        user = request.user
        return bool(
            user.is_authenticated
            and user.is_active
            and not user.is_blocked
            and user.role == Role.ADMIN
        )
