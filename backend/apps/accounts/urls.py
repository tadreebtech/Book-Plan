from django.urls import path

from apps.accounts.apis import (
    UserBlockApi,
    UserDetailApi,
    UserListApi,
    UserRoleChangeApi,
    UserUnblockApi,
)

urlpatterns = [
    path("admin/users/", UserListApi.as_view(), name="admin-user-list"),
    path("admin/users/<str:user_id>/", UserDetailApi.as_view(), name="admin-user-detail"),
    path("admin/users/<str:user_id>/block/", UserBlockApi.as_view(), name="admin-user-block"),
    path("admin/users/<str:user_id>/unblock/", UserUnblockApi.as_view(), name="admin-user-unblock"),
    path("admin/users/<str:user_id>/role/", UserRoleChangeApi.as_view(), name="admin-user-role"),
]
