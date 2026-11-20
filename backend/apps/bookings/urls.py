from django.urls import path
from rest_framework.routers import SimpleRouter

from apps.bookings.views import AdminListingListApi, BookingViewSet

from .catalog_apis import CatalogListingListApi, ProviderListingListApi

router = SimpleRouter()
router.register("bookings", BookingViewSet, basename="booking")

urlpatterns = [
    path("admin/listings/", AdminListingListApi.as_view(), name="admin-listing-list"),
    *router.urls,
    path("listings/", CatalogListingListApi.as_view(), name="catalog-listing-list"),
    path("provider/listings/", ProviderListingListApi.as_view(), name="provider-listing-list"),
]
