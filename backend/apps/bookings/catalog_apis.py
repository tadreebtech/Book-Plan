from rest_framework import serializers
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import IsManagerRole
from apps.bookings.models import Resource
from apps.bookings.selectors import catalog_resource_list, resource_list
from apps.bookings.serializers import ListingQuerySerializer


class CatalogListingListApi(APIView):
    """Класс, возвращающий клиентский каталог объявлений"""

    permission_classes = (IsAuthenticated,)
    InputSerializer = ListingQuerySerializer

    class OutputSerializer(serializers.ModelSerializer):
        """Класс, представляющий объявление в клиентском каталоге"""

        title = serializers.CharField(source="name", read_only=True)
        category = serializers.CharField(source="kind", read_only=True)

        class Meta:
            """Класс, задающий поля объявления для клиентского каталога"""

            model = Resource
            fields = ("id", "title", "category", "capacity")
            read_only_fields = fields

    def get(self, request: Request) -> Response:
        """Метод, возвращающий страницу клиентского каталога"""

        query = self.InputSerializer(data=request.query_params.dict())
        query.is_valid(raise_exception=True)
        params = query.validated_data
        count, listings = catalog_resource_list(**params)
        return Response(
            {
                "count": count,
                "page": params["page"],
                "page_size": params["page_size"],
                "results": self.OutputSerializer(listings, many=True).data,
            }
        )


class ProviderListingListApi(APIView):
    """Класс, возвращающий поставщику его объявления во всех статусах"""

    permission_classes = (IsAuthenticated, IsManagerRole)
    InputSerializer = ListingQuerySerializer

    class OutputSerializer(CatalogListingListApi.OutputSerializer):
        """Класс, представляющий объявление со статусом и причиной отклонения"""

        class Meta(CatalogListingListApi.OutputSerializer.Meta):
            """Класс, задающий поля объявления для поставщика"""

            fields = CatalogListingListApi.OutputSerializer.Meta.fields + (
                "is_active",
                "moderation_status",
                "rejection_reason",
            )
            read_only_fields = fields

    def get(self, request: Request) -> Response:
        """Метод, возвращающий страницу объявлений текущего поставщика"""

        query = self.InputSerializer(data=request.query_params.dict())
        query.is_valid(raise_exception=True)
        params = query.validated_data
        count, listings = resource_list(provider=request.user.pk, **params)
        return Response(
            {
                "count": count,
                "page": params["page"],
                "page_size": params["page_size"],
                "results": self.OutputSerializer(listings, many=True).data,
            }
        )
