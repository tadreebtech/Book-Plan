from django.urls import path
from rest_framework.routers import SimpleRouter

from apps.bookings.apis import CategoryDetailApi, CategoryListCreateApi
from apps.bookings.views import AdminListingListApi, BookingViewSet

router = SimpleRouter()
router.register("bookings", BookingViewSet, basename="booking")

urlpatterns = [
    path("admin/listings/", AdminListingListApi.as_view(), name="admin-listing-list"),
    path("admin/categories/", CategoryListCreateApi.as_view(), name="admin-category-list"),
    path(
        "admin/categories/<str:category_id>/",
        CategoryDetailApi.as_view(),
        name="admin-category-detail",
    ),
    *router.urls,
]
