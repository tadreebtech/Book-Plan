from django.db.models import Q, QuerySet

from apps.bookings.models import Category, Reference, Resource


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


def category_list(
    *, search: str = "", page: int = 1, page_size: int = 20
) -> tuple[int, QuerySet[Category]]:
    """Функция, возвращающая количество найденных категорий и выбранную страницу"""

    categories = Category.objects.order_by("name", "pk")
    if search:
        categories = categories.filter(
            Q(name__icontains=search) | Q(slug__icontains=search) | Q(description__icontains=search)
        )
    count = categories.count()
    start = (page - 1) * page_size
    if start >= count:
        return count, categories.none()
    return count, categories[start : start + page_size]


def category_get(*, category_id: int) -> Category | None:
    """Функция, возвращающая категорию по идентификатору"""

    return Category.objects.filter(pk=category_id).first()


def reference_list(
    *, reference_type: str | None = None, page: int = 1, page_size: int = 20
) -> tuple[int, QuerySet[Reference]]:
    """Функция, возвращающая количество значений справочника и выбранную страницу"""

    references = Reference.objects.order_by("type", "value", "pk")
    if reference_type is not None:
        references = references.filter(type=reference_type)
    count = references.count()
    start = (page - 1) * page_size
    if start >= count:
        return count, references.none()
    return count, references[start : start + page_size]
