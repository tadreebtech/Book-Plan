from django.urls import path

from apps.bookings.apis import BookingCancelApi, BookingDetailApi, BookingListCreateApi

urlpatterns = [
    path("bookings/", BookingListCreateApi.as_view(), name="booking-list-create"),
    path("bookings/<int:booking_id>/", BookingDetailApi.as_view(), name="booking-detail"),
    path("bookings/<int:booking_id>/cancel/", BookingCancelApi.as_view(), name="booking-cancel"),
]
