import pytest
from django.db import connection
from django.db.migrations.executor import MigrationExecutor

from apps.bookings.models import ModerationStatus, Resource, ResourceKind


@pytest.mark.django_db(transaction=True)
def test_resource_moderation_migration_preserves_existing_visibility():
    before = [("bookings", "0001_initial")]
    after = [("bookings", "0002_resource_moderation")]

    executor = MigrationExecutor(connection)
    try:
        old_apps = executor.migrate(before).apps
        old_resource = old_apps.get_model("bookings", "Resource")
        active = old_resource.objects.create(
            name="Active room", kind=ResourceKind.HOTEL_ROOM, capacity=2
        )
        inactive = old_resource.objects.create(
            name="Inactive room", kind=ResourceKind.HOTEL_ROOM, capacity=2, is_active=False
        )

        MigrationExecutor(connection).migrate(after)

        active_listing = Resource.objects.get(pk=active.pk)
        inactive_listing = Resource.objects.get(pk=inactive.pk)
        assert active_listing.moderation_status == ModerationStatus.APPROVED
        assert active_listing.is_active is True
        assert inactive_listing.moderation_status == ModerationStatus.HIDDEN
        assert inactive_listing.is_active is False
        assert active_listing.moderated_at is None
        assert active_listing.moderated_by_id is None

        new_listing = Resource.objects.create(
            name="New room", kind=ResourceKind.HOTEL_ROOM, capacity=2
        )
        new_listing.refresh_from_db()
        assert new_listing.moderation_status == ModerationStatus.PENDING
        assert new_listing.rejection_reason == ""
    finally:
        executor = MigrationExecutor(connection)
        executor.migrate(executor.loader.graph.leaf_nodes())
