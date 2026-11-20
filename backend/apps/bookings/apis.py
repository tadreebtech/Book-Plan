from rest_framework import serializers, status
from rest_framework.exceptions import NotFound
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import IsAdminRole
from apps.bookings.models import Category, Reference
from apps.bookings.selectors import category_get, category_list, reference_list
from apps.bookings.services import (
    category_create,
    category_delete,
    category_update,
    reference_create,
    reference_delete,
    reference_update,
)


class ObjectIdSerializer(serializers.Serializer):
    """Класс, проверяющий идентификатор объекта из адреса запроса"""

    id = serializers.IntegerField(min_value=1, max_value=2**63 - 1)


def _object_id(value: str) -> int:
    """Функция, возвращающая проверенный идентификатор из адреса запроса"""

    serializer = ObjectIdSerializer(data={"id": value})
    serializer.is_valid(raise_exception=True)
    return serializer.validated_data["id"]


class CategoryListCreateApi(APIView):
    """Класс, предоставляющий список и создание категорий администратору"""

    permission_classes = [IsAuthenticated, IsAdminRole]

    class FilterSerializer(serializers.Serializer):
        """Класс, проверяющий параметры поиска и пагинации категорий"""

        search = serializers.CharField(max_length=255, allow_blank=True, default="")
        page = serializers.IntegerField(min_value=1, default=1)
        page_size = serializers.IntegerField(min_value=1, max_value=100, default=20)

    class InputSerializer(serializers.Serializer):
        """Класс, проверяющий свойства создаваемой или изменяемой категории"""

        name = serializers.CharField(max_length=255)
        slug = serializers.SlugField(max_length=255)
        description = serializers.CharField(allow_blank=True, default="")
        is_active = serializers.BooleanField(default=True)

    class OutputSerializer(serializers.ModelSerializer):
        """Класс, представляющий категорию в ответе API"""

        class Meta:
            """Класс, задающий поля категории в ответе"""

            model = Category
            fields = ("id", "name", "slug", "description", "is_active")
            read_only_fields = fields

    def get(self, request: Request) -> Response:
        """Метод, возвращающий страницу категорий с поиском"""

        query = self.FilterSerializer(data=request.query_params.dict())
        query.is_valid(raise_exception=True)
        params = query.validated_data
        count, categories = category_list(**params)
        return Response(
            {
                "count": count,
                "page": params["page"],
                "page_size": params["page_size"],
                "results": self.OutputSerializer(categories, many=True).data,
            }
        )

    def post(self, request: Request) -> Response:
        """Метод, создающий категорию с проверенными свойствами"""

        serializer = self.InputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        category = category_create(**serializer.validated_data)
        return Response(self.OutputSerializer(category).data, status=status.HTTP_201_CREATED)


class CategoryDetailApi(APIView):
    """Класс, предоставляющий просмотр, изменение и удаление категории"""

    permission_classes = [IsAuthenticated, IsAdminRole]
    InputSerializer = CategoryListCreateApi.InputSerializer
    OutputSerializer = CategoryListCreateApi.OutputSerializer

    def get(self, request: Request, category_id: str) -> Response:
        """Метод, возвращающий карточку категории"""

        category = category_get(category_id=_object_id(category_id))
        if category is None:
            raise NotFound()
        return Response(self.OutputSerializer(category).data)

    def patch(self, request: Request, category_id: str) -> Response:
        """Метод, изменяющий только переданные свойства категории"""

        serializer = self.InputSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        category = category_update(category_id=_object_id(category_id), **serializer.validated_data)
        return Response(self.OutputSerializer(category).data)

    def delete(self, request: Request, category_id: str) -> Response:
        """Метод, удаляющий неиспользуемую категорию"""

        category_delete(category_id=_object_id(category_id))
        return Response(status=status.HTTP_204_NO_CONTENT)


class ReferenceListCreateApi(APIView):
    """Класс, предоставляющий список и создание значений справочников"""

    permission_classes = [IsAuthenticated, IsAdminRole]

    class FilterSerializer(serializers.Serializer):
        """Класс, проверяющий тип справочника и параметры страницы"""

        type = serializers.CharField(source="reference_type", max_length=64, required=False)
        page = serializers.IntegerField(min_value=1, default=1)
        page_size = serializers.IntegerField(min_value=1, max_value=100, default=20)

    class InputSerializer(serializers.Serializer):
        """Класс, проверяющий свойства значения справочника"""

        type = serializers.CharField(source="reference_type", max_length=64)
        value = serializers.CharField(max_length=255)
        is_active = serializers.BooleanField(default=True)

    class OutputSerializer(serializers.ModelSerializer):
        """Класс, представляющий значение справочника в ответе API"""

        class Meta:
            """Класс, задающий поля значения справочника в ответе"""

            model = Reference
            fields = ("id", "type", "value", "is_active")
            read_only_fields = fields

    def get(self, request: Request) -> Response:
        """Метод, возвращающий страницу значений с фильтром по типу справочника"""

        query = self.FilterSerializer(data=request.query_params.dict())
        query.is_valid(raise_exception=True)
        params = query.validated_data
        count, references = reference_list(**params)
        return Response(
            {
                "count": count,
                "page": params["page"],
                "page_size": params["page_size"],
                "results": self.OutputSerializer(references, many=True).data,
            }
        )

    def post(self, request: Request) -> Response:
        """Метод, создающий значение справочника с проверенными свойствами"""

        serializer = self.InputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        reference = reference_create(**serializer.validated_data)
        return Response(self.OutputSerializer(reference).data, status=status.HTTP_201_CREATED)


class ReferenceDetailApi(APIView):
    """Класс, предоставляющий изменение и удаление значения справочника"""

    permission_classes = [IsAuthenticated, IsAdminRole]
    InputSerializer = ReferenceListCreateApi.InputSerializer
    OutputSerializer = ReferenceListCreateApi.OutputSerializer

    def patch(self, request: Request, reference_id: str) -> Response:
        """Метод, изменяющий переданные свойства значения справочника"""

        serializer = self.InputSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        reference = reference_update(
            reference_id=_object_id(reference_id), **serializer.validated_data
        )
        return Response(self.OutputSerializer(reference).data)

    def delete(self, request: Request, reference_id: str) -> Response:
        """Метод, удаляющий неиспользуемое значение справочника"""

        reference_delete(reference_id=_object_id(reference_id))
        return Response(status=status.HTTP_204_NO_CONTENT)
