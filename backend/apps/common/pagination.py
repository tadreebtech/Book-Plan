from django.db.models import QuerySet
from rest_framework import serializers

MAX_DB_ID = 2**63 - 1


class PaginationInputSerializer(serializers.Serializer):
    """Класс, проверяющий номер и размер страницы в списочных API"""

    page = serializers.IntegerField(min_value=1, default=1)
    page_size = serializers.IntegerField(min_value=1, max_value=100, default=20)


def paginated_response_data(
    *,
    queryset: QuerySet,
    serializer_class: type[serializers.Serializer],
    page: int,
    page_size: int,
) -> dict:
    """Функция, собирающая страницу списка в общем для API формате ответа"""

    count = queryset.count()
    start = (page - 1) * page_size
    results = (
        serializer_class(queryset[start : start + page_size], many=True).data
        if start < count
        else []
    )
    return {"count": count, "page": page, "page_size": page_size, "results": results}
