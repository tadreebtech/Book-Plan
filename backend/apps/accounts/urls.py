from django.urls import path

from apps.accounts.apis import UserListApi

urlpatterns = [
    path("admin/users/", UserListApi.as_view(), name="admin-user-list"),
]
