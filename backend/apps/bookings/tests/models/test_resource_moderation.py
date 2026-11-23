import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, connection, transaction
from django.db.migrations.executor import MigrationExecutor
from django.db.models.deletion import ProtectedError
from django.utils import timezone

from apps.accounts.models import Role, User
from apps.bookings.models import ModerationStatus, Resource, ResourceKind

pytestmark = pytest.mark.django_db


@pytest.fixture
def moderator():
    return User.objects.create_user(username="moderator", role=Role.ADMIN)


@pytest.fixture
def rejected_resource(moderator):
    return Resource(
        name="Rejected room",
        kind=ResourceKind.HOTEL_ROOM,
        capacity=2,
        moderation_status=ModerationStatus.REJECTED,
        rejection_reason="The listing contains incorrect information.",
        moderated_at=timezone.now(),
        moderated_by=moderator,
    )


@pytest.mark.parametrize(
    "changes",
    [
        {"rejection_reason": ""},
        {"rejection_reason": "  \t\n"},
        {"moderated_at": None},
        {"moderated_by": None},
        {"moderation_status": ModerationStatus.PENDING},
        {
            "moderation_status": ModerationStatus.PENDING,
            "rejection_reason": "",
            "moderated_by": None,
        },
        {
            "moderation_status": ModerationStatus.PENDING,
            "rejection_reason": "",
            "moderated_at": None,
        },
        {"moderation_status": ModerationStatus.APPROVED},
        {
            "moderation_status": ModerationStatus.APPROVED,
            "rejection_reason": "",
            "moderated_by": None,
        },
        {
            "moderation_status": ModerationStatus.APPROVED,
            "rejection_reason": "",
            "moderated_at": None,
        },
        {"moderation_status": ModerationStatus.HIDDEN},
        {
            "moderation_status": ModerationStatus.HIDDEN,
            "rejection_reason": "",
            "moderated_by": None,
        },
    ],
)
def test_inconsistent_moderation_fails_model_validation_and_database(rejected_resource, changes):
    for field, value in changes.items():
        setattr(rejected_resource, field, value)

    with pytest.raises(ValidationError):
        rejected_resource.full_clean()
    with pytest.raises(IntegrityError), transaction.atomic():
        rejected_resource.save()


@pytest.mark.parametrize("status", ModerationStatus.values)
def test_consistent_moderation_can_be_validated_and_saved(rejected_resource, status):
    rejected_resource.moderation_status = status
    if status != ModerationStatus.REJECTED:
        rejected_resource.rejection_reason = ""
    if status == ModerationStatus.PENDING:
        rejected_resource.moderated_at = None
        rejected_resource.moderated_by = None

    rejected_resource.full_clean()
    rejected_resource.save()
    rejected_resource.refresh_from_db()
    assert rejected_resource.moderation_status == status


def test_moderation_constraint_also_applies_to_queryset_updates(rejected_resource):
    rejected_resource.save()

    with pytest.raises(IntegrityError), transaction.atomic():
        Resource.objects.filter(pk=rejected_resource.pk).update(rejection_reason="")

    rejected_resource.refresh_from_db()
    assert rejected_resource.rejection_reason


def test_moderator_deletion_preserves_moderation_history(rejected_resource, moderator):
    rejected_resource.save()

    with pytest.raises(ProtectedError):
        moderator.delete()

    rejected_resource.refresh_from_db()
    assert rejected_resource.moderated_by_id == moderator.pk


@pytest.mark.django_db(transaction=True)
def test_resource_moderation_migration_preserves_existing_visibility():
    before = [("bookings", "0001_initial")]
    schema = [("bookings", "0002_resource_moderation")]
    after = [("bookings", "0003_populate_resource_moderation")]

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

        schema_apps = MigrationExecutor(connection).migrate(schema).apps
        schema_resource = schema_apps.get_model("bookings", "Resource")
        assert set(schema_resource.objects.values_list("moderation_status", flat=True)) == {
            ModerationStatus.PENDING
        }
        MigrationExecutor(connection).migrate(after)

        active_listing = Resource.objects.get(pk=active.pk)
        inactive_listing = Resource.objects.get(pk=inactive.pk)
        assert active_listing.moderation_status == ModerationStatus.APPROVED
        assert active_listing.is_active is True
        assert inactive_listing.moderation_status == ModerationStatus.HIDDEN
        assert inactive_listing.is_active is False
        assert active_listing.moderated_at is None
        assert active_listing.moderated_by_id is None
        active_listing.full_clean()
        inactive_listing.full_clean()

        new_listing = Resource.objects.create(
            name="New room", kind=ResourceKind.HOTEL_ROOM, capacity=2
        )
        new_listing.refresh_from_db()
        assert new_listing.moderation_status == ModerationStatus.PENDING
        assert new_listing.rejection_reason == ""
    finally:
        executor = MigrationExecutor(connection)
        executor.migrate(executor.loader.graph.leaf_nodes())
