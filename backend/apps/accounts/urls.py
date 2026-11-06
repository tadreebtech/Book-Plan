from django.urls import path

from apps.accounts.apis import UserDetailApi, UserListApi

urlpatterns = [
    path("admin/users/", UserListApi.as_view(), name="admin-user-list"),
    path("admin/users/<str:user_id>/", UserDetailApi.as_view(), name="admin-user-detail"),
]
