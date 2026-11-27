from django.urls import path
from rest_framework.routers import SimpleRouter

from apps.bookings.activation_apis import AdminListingActivateApi, AdminListingDeactivateApi
from apps.bookings.apis import BookingDetailApi, BookingListApi
from apps.bookings.views import AdminListingListApi, BookingViewSet

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
]
