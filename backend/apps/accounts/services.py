from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework.exceptions import PermissionDenied

from apps.accounts.models import AuditAction, AuditLog, Role, User


def _user_set_blocked(*, actor: User, user_id: int, is_blocked: bool) -> User:
    """Функция, атомарно меняющая статус пользователя и записывающая действие в аудит"""

    if not actor.is_active or actor.is_blocked or actor.role != Role.ADMIN:
        raise PermissionDenied()

    with transaction.atomic():
        user = get_object_or_404(User.objects.select_for_update(), pk=user_id)
        if is_blocked and (user.pk == actor.pk or user.role == Role.ADMIN):
            raise PermissionDenied()

        if user.is_blocked != is_blocked:
            user.is_blocked = is_blocked
            user.full_clean()
            user.save(update_fields=["is_blocked", "updated_at"])

            audit_log = AuditLog(
                actor=actor,
                action=AuditAction.USER_BLOCKED if is_blocked else AuditAction.USER_UNBLOCKED,
                target=user,
            )
            audit_log.full_clean()
            audit_log.save()

        return user


def user_block(*, actor: User, user_id: int) -> User:
    """Функция, блокирующая пользователя по запросу администратора"""

    return _user_set_blocked(actor=actor, user_id=user_id, is_blocked=True)


def user_unblock(*, actor: User, user_id: int) -> User:
    """Функция, снимающая блокировку пользователя по запросу администратора"""

    return _user_set_blocked(actor=actor, user_id=user_id, is_blocked=False)
