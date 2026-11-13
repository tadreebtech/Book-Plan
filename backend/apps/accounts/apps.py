from django.apps import AppConfig


class AccountsConfig(AppConfig):
    """Класс, подключающий модуль пользователей к Django"""

    name = "apps.accounts"
    verbose_name = "Пользователи"
