from types import SimpleNamespace

import pytest
from django.contrib import admin
from django.test import RequestFactory

from apps.accounts.admin import BookPlanUserAdmin
from apps.accounts.models import AuditAction, AuditLog, Role, User

pytestmark = pytest.mark.django_db


def save_role(actor: User, target: User, new_role: str) -> list[str]:
    """Функция, сохраняющая новую роль пользователя через админку и возвращающая сообщения"""

    user_admin = BookPlanUserAdmin(User, admin.site)
    messages_sent: list[str] = []
    user_admin.message_user = lambda request, message, level=None: messages_sent.append(message)
    request = RequestFactory().post("/")
    request.user = actor
    form = SimpleNamespace(changed_data=["role"], initial={"role": target.role})
    target.role = new_role
    user_admin.save_model(request, target, form, change=True)
    return messages_sent


@pytest.fixture
def admin_user() -> User:
    """Функция, создающая администратора для работы в админке"""

    return User.objects.create_user(username="admin", role=Role.ADMIN)


def test_admin_role_change_is_saved_with_audit(admin_user: User) -> None:
    """Функция, проверяющая смену роли в админке с записью в аудит"""

    target = User.objects.create_user(username="target", role=Role.CLIENT)

    messages_sent = save_role(admin_user, target, Role.MANAGER)

    target.refresh_from_db()
    assert messages_sent == []
    assert target.role == Role.MANAGER
    audit_log = AuditLog.objects.get()
    assert audit_log.action == AuditAction.CHANGE_ROLE
    assert (audit_log.old_value, audit_log.new_value) == (Role.CLIENT, Role.MANAGER)


def test_admin_cannot_remove_own_admin_role(admin_user: User) -> None:
    """Функция, проверяющая запрет снять с себя роль администратора в админке"""

    messages_sent = save_role(admin_user, admin_user, Role.CLIENT)

    admin_user.refresh_from_db()
    assert len(messages_sent) == 1
    assert admin_user.role == Role.ADMIN
    assert AuditLog.objects.count() == 0


def test_non_admin_cannot_change_role() -> None:
    """Функция, проверяющая запрет смены роли для сотрудника без роли администратора"""

    staff = User.objects.create_user(username="staff", role=Role.CLIENT, is_staff=True)
    target = User.objects.create_user(username="target", role=Role.CLIENT)

    messages_sent = save_role(staff, target, Role.ADMIN)

    target.refresh_from_db()
    assert len(messages_sent) == 1
    assert target.role == Role.CLIENT
    assert AuditLog.objects.count() == 0
