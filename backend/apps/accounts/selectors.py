from django.db.models import Q, QuerySet, Value
from django.db.models.functions import Concat

from apps.accounts.models import User


def user_list(
    *,
    search: str = "",
    role: str | None = None,
    is_active: bool | None = None,
    ordering: str = "-created_at",
) -> QuerySet[User]:
    """Функция, выбирающая пользователей по поиску, фильтрам и порядку сортировки"""

    users = User.objects.all()

    if search:
        users = users.annotate(full_name=Concat("first_name", Value(" "), "last_name")).filter(
            Q(email__icontains=search)
            | Q(username__icontains=search)
            | Q(first_name__icontains=search)
            | Q(last_name__icontains=search)
            | Q(full_name__icontains=search)
        )

    if role is not None:
        users = users.filter(role=role)

    if is_active is not None:
        users = users.filter(is_active=is_active)

    secondary_ordering = "-id" if ordering.startswith("-") else "id"
    return users.order_by(ordering, secondary_ordering)
