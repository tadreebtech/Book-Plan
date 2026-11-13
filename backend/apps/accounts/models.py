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
