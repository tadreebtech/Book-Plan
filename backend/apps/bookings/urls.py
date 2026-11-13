from django.urls import path
from rest_framework.routers import SimpleRouter

from apps.bookings.apis import BookingListApi
from apps.bookings.views import BookingViewSet

router = SimpleRouter()
router.register("bookings", BookingViewSet, basename="booking")

urlpatterns = [
    path("admin/bookings/", BookingListApi.as_view(), name="admin-booking-list"),
    *router.urls,
]
