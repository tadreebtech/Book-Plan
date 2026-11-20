import pytest
from django.db import connection
from django.db.migrations.executor import MigrationExecutor


@pytest.mark.django_db(transaction=True)
def test_category_migration_preserves_existing_resources() -> None:
    """Функция, проверяющая сохранность ресурсов при добавлении категорий"""

    executor = MigrationExecutor(connection)
    try:
        old_apps = executor.migrate([("bookings", "0001_initial")]).apps
        old_resource = old_apps.get_model("bookings", "Resource")
        resource = old_resource.objects.create(name="Existing room", kind="HOTEL_ROOM", capacity=2)

        apps = MigrationExecutor(connection).migrate([("bookings", "0004_category_schema")]).apps
        restored = apps.get_model("bookings", "Resource").objects.get(pk=resource.pk)

        assert restored.name == "Existing room"
        assert restored.category_id is None
        assert restored.is_active is True
    finally:
        executor = MigrationExecutor(connection)
        executor.migrate(executor.loader.graph.leaf_nodes())
