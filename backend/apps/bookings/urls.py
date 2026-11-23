from django.urls import path
from rest_framework.routers import SimpleRouter

from apps.bookings.activation_apis import AdminListingActivateApi, AdminListingDeactivateApi
from apps.bookings.apis import (
    BookingDetailApi, BookingListApi,
    AdminListingApproveApi, AdminListingHideApi, AdminListingRejectApi,
)
from apps.bookings.views import AdminListingListApi, BookingViewSet

from .catalog_apis import CatalogListingListApi, ProviderListingListApi

router = SimpleRouter()
router.register("bookings", BookingViewSet, basename="booking")

urlpatterns = [
    path("admin/bookings/", BookingListApi.as_view(), name="admin-booking-list"),
    path(
        "admin/bookings/<str:booking_id>/",
        BookingDetailApi.as_view(),
        name="admin-booking-detail",
    ),
    path("admin/listings/", AdminListingListApi.as_view(), name="admin-listing-list"),
    path(
        "admin/listings/<str:resource_id>/approve/",
        AdminListingApproveApi.as_view(),
        name="admin-listing-approve",
    ),
    path(
        "admin/listings/<str:resource_id>/reject/",
        AdminListingRejectApi.as_view(),
        name="admin-listing-reject",
    ),
    path(
        "admin/listings/<str:resource_id>/hide/",
        AdminListingHideApi.as_view(),
        name="admin-listing-hide",
    ),
    path(
        "admin/listings/<str:resource_id>/activate/",
        AdminListingActivateApi.as_view(),
        name="admin-listing-activate",
    ),
    path(
        "admin/listings/<str:resource_id>/deactivate/",
        AdminListingDeactivateApi.as_view(),
        name="admin-listing-deactivate",
    ),
    *router.urls,
    path("listings/", CatalogListingListApi.as_view(), name="catalog-listing-list"),
    path("provider/listings/", ProviderListingListApi.as_view(), name="provider-listing-list"),
]
