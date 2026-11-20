from django.db.models import QuerySet

from apps.bookings.models import Resource


def resource_list(
    *,
    moderation_status: str | None = None,
    category: str | None = None,
    provider: int | None = None,
    search: str = "",
    page: int = 1,
    page_size: int = 20,
) -> tuple[int, QuerySet[Resource]]:
    """Функция, возвращающая количество найденных объявлений и выбранную страницу"""

    resources = Resource.objects.order_by("-created_at", "-pk")
    if moderation_status is not None:
        resources = resources.filter(moderation_status=moderation_status)
    if category is not None:
        resources = resources.filter(kind=category)
    if provider is not None:
        resources = resources.filter(manager_id=provider)
    if search:
        resources = resources.filter(name__icontains=search)

    count = resources.count()
    start = (page - 1) * page_size
    if start >= count:
        return count, resources.none()
    return count, resources[start : start + page_size]
