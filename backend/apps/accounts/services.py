from django.db import transaction
from rest_framework.exceptions import PermissionDenied

from apps.accounts.models import AuditAction, AuditLog, Role, User


def _user_set_active(*, actor: User, user_id: int, is_active: bool) -> User:
    """Функция, атомарно меняющая активность пользователя и записывающая действие в аудит"""

    if not actor.is_active or actor.role != Role.ADMIN:
        raise PermissionDenied()

    with transaction.atomic():
        user = User.objects.select_for_update().get(pk=user_id)
        if not is_active and (user.pk == actor.pk or user.role == Role.ADMIN):
            raise PermissionDenied()

        if user.is_active != is_active:
            user.is_active = is_active
            user.full_clean()
            user.save(update_fields=["is_active", "updated_at"])

            audit_log = AuditLog(
                actor=actor,
                action=AuditAction.USER_UNBLOCKED if is_active else AuditAction.USER_BLOCKED,
                target=user,
            )
            audit_log.full_clean()
            audit_log.save()

        return user


def user_block(*, actor: User, user_id: int) -> User:
    """Функция, блокирующая пользователя по запросу администратора"""

    return _user_set_active(actor=actor, user_id=user_id, is_active=False)


def user_unblock(*, actor: User, user_id: int) -> User:
    """Функция, снимающая блокировку пользователя по запросу администратора"""

    return _user_set_active(actor=actor, user_id=user_id, is_active=True)


def user_role_change(*, actor: User, user_id: int, role: str) -> User:
    """Функция, меняющая роль пользователя и записывающая прежнюю и новую роль в аудит"""

    if not actor.is_active or actor.role != Role.ADMIN:
        raise PermissionDenied()

    with transaction.atomic():
        user = User.objects.select_for_update().get(pk=user_id)
        if user.role != role:
            old_role = user.role
            user.role = role
            user.full_clean()
            user.save(update_fields=["role", "updated_at"])

            audit_log = AuditLog(
                actor=actor,
                action=AuditAction.CHANGE_ROLE,
                target=user,
                old_value=old_role,
                new_value=role,
            )
            audit_log.full_clean()
            audit_log.save()

        return user
