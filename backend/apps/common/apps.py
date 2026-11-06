from django.apps import AppConfig


class CommonConfig(AppConfig):
    """Класс, подключающий к Django общий модуль с базовой моделью и обработкой ошибок API"""

    name = "apps.common"
    verbose_name = "Common"
