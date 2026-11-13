from django.apps import AppConfig


class BookingsConfig(AppConfig):
    """Класс, подключающий модуль бронирований к Django"""

    name = "apps.bookings"
    verbose_name = "Бронирования"
