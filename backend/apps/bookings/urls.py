from django.urls import path
from rest_framework.routers import SimpleRouter

from apps.bookings.views import AdminListingListApi, BookingViewSet

router = SimpleRouter()
router.register("bookings", BookingViewSet, basename="booking")

urlpatterns = [
    path("admin/listings/", AdminListingListApi.as_view(), name="admin-listing-list"),
    *router.urls,
]
