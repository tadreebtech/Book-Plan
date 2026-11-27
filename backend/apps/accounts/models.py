from django.contrib.auth.models import AbstractUser
from django.db import models

from apps.common.models import BaseModel


class Role(models.TextChoices):
    """Класс, перечисляющий роли пользователей: клиент, менеджер ресурса, администратор"""

    CLIENT = "CLIENT", "Клиент"
    MANAGER = "MANAGER", "Менеджер ресурса"
    ADMIN = "ADMIN", "Администратор"


class User(BaseModel, AbstractUser):
    """Класс, описывающий пользователя платформы: логин, пароль, email и роль"""

    role = models.CharField(max_length=16, choices=Role.choices, default=Role.CLIENT)

    class Meta:
        """Класс, задающий правила таблицы пользователей, которые проверяет сама база данных"""

        constraints = [
            models.CheckConstraint(
                condition=models.Q(role__in=Role.values), name="user_role_valid"
            ),
        ]


class AuditAction(models.TextChoices):
    """Класс, перечисляющий действия администратора над учётной записью пользователя"""

    CHANGE_ROLE = "CHANGE_ROLE", "Роль пользователя изменена"
    USER_BLOCKED = "USER_BLOCKED", "Пользователь заблокирован"
    USER_UNBLOCKED = "USER_UNBLOCKED", "Пользователь разблокирован"


class AuditLog(BaseModel):
    """Класс, сохраняющий автора, действие, пользователя, время и прежнее и новое значение"""

    actor = models.ForeignKey(User, on_delete=models.PROTECT, related_name="status_actions")
    action = models.CharField(max_length=32, choices=AuditAction.choices)
    target = models.ForeignKey(User, on_delete=models.PROTECT, related_name="status_audit_log")
    old_value = models.CharField(max_length=32, blank=True)
    new_value = models.CharField(max_length=32, blank=True)

    class Meta:
        """Класс, ограничивающий допустимые действия в журнале аудита"""

        constraints = [
            models.CheckConstraint(
                condition=models.Q(action__in=AuditAction.values), name="audit_action_valid"
            ),
        ]
