from django.urls import path
from rest_framework.routers import SimpleRouter

from apps.bookings.apis import AdminListingApproveApi, AdminListingHideApi, AdminListingRejectApi
from apps.bookings.views import AdminListingListApi, BookingViewSet

router = SimpleRouter()
router.register("bookings", BookingViewSet, basename="booking")

urlpatterns = [
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
    *router.urls,
]
