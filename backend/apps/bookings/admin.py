from django.contrib import admin

from .models import Booking, Resource

@admin.register(Resource)
class ResourceAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "kind", "capacity", "is_active")
    list_filter = ("kind", "is_active")


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ("id", "resource", "user", "start_at", "end_at", "status")
    list_filter = ("status",)