from datetime import datetime

from django.db import IntegrityError, transaction
from django.db.models import QuerySet
from django.utils import timezone
from rest_framework.exceptions import NotFound, ValidationError

from apps.accounts.models import User
from apps.bookings.exceptions import (
    BookingConflict,
    BookingValidationError,
    CategoryInUse,
    ReferenceInUse,
    ResourceUnavailable,
)
from apps.bookings.models import (
    Booking,
    BookingStatus,
    Category,
    Reference,
    Resource,
    ResourceStatus,
)


def _is_overlap_constraint_error(exc: IntegrityError) -> bool:
    cause = exc.__cause__
    diag = getattr(cause, "diag", None)
    constraint_name = getattr(diag, "constraint_name", None)
    return constraint_name == "booking_no_overlap" or "booking_no_overlap" in str(exc)


def create_booking(
    *, user: User, resource: Resource, start_at: datetime, end_at: datetime, guests: int
) -> Booking:
    if timezone.is_naive(start_at) or timezone.is_naive(end_at):
        raise BookingValidationError("Dates must include a timezone.")

    if start_at >= end_at:
        raise BookingValidationError("End time must be after start time.")

    if start_at <= timezone.now():
        raise BookingValidationError("Start time must be in the future.")

    if guests < 1:
        raise BookingValidationError("Guests must be at least 1.")

    try:
        with transaction.atomic():
            try:
                locked_resource = Resource.objects.select_for_update().get(pk=resource.pk)
            except Resource.DoesNotExist as exc:
                raise NotFound("Resource not found.") from exc

            if not locked_resource.is_active or locked_resource.status == ResourceStatus.ARCHIVED:
                raise ResourceUnavailable("Resource is unavailable.")

            if guests > locked_resource.capacity:
                raise BookingValidationError(
                    "Guests exceed resource capacity.",
                    code="CAPACITY_EXCEEDED",
                )

            overlap_exists = (
                Booking.objects.filter(
                    resource=locked_resource,
                    start_at__lt=end_at,
                    end_at__gt=start_at,
                )
                .exclude(status=BookingStatus.CANCELLED)
                .exists()
            )

            if overlap_exists:
                raise BookingConflict("Resource is already booked for this time slot.")

            return Booking.objects.create(
                resource=locked_resource,
                user=user,
                start_at=start_at,
                end_at=end_at,
                guests=guests,
                status=BookingStatus.CONFIRMED,
            )
    except IntegrityError as exc:
        if _is_overlap_constraint_error(exc):
            raise BookingConflict("Resource is already booked for this time slot.") from exc
        raise


def list_user_bookings(*, user: User) -> QuerySet[Booking]:
    return Booking.objects.filter(user=user).select_related("resource").order_by("-start_at", "-pk")


def cancel_booking(*, user: User, booking_id: int) -> Booking:
    with transaction.atomic():
        try:
            booking = (
                Booking.objects.select_for_update()
                .select_related("resource")
                .get(pk=booking_id, user=user)
            )
        except Booking.DoesNotExist as exc:
            raise NotFound("Booking not found.") from exc

        if booking.status == BookingStatus.CANCELLED:
            raise BookingConflict("Booking is already cancelled.", code="ALREADY_CANCELLED")

        if booking.status == BookingStatus.COMPLETED or booking.end_at <= timezone.now():
            raise BookingConflict(
                "Completed bookings cannot be cancelled.",
                code="BOOKING_COMPLETED",
            )

        booking.status = BookingStatus.CANCELLED
        booking.save(update_fields=["status", "updated_at"])
        return booking


def _category_save(*, category: Category) -> Category:
    """Функция, сохраняющая категорию и обрабатывающая одновременное создание одинаковых slug"""

    try:
        with transaction.atomic():
            category.full_clean()
            category.save()
    except IntegrityError as exc:
        constraint = getattr(getattr(exc.__cause__, "diag", None), "constraint_name", None)
        if constraint == f"{Category._meta.db_table}_slug_key":
            raise ValidationError({"slug": ["A category with this slug already exists."]}) from exc
        raise
    return category


def category_create(
    *, name: str, slug: str, description: str = "", is_active: bool = True
) -> Category:
    """Функция, создающая категорию с уникальным slug"""

    return _category_save(
        category=Category(name=name, slug=slug, description=description, is_active=is_active)
    )


@transaction.atomic
def category_update(*, category_id: int, **fields: object) -> Category:
    """Функция, изменяющая переданные свойства категории"""

    try:
        category = Category.objects.select_for_update().get(pk=category_id)
    except Category.DoesNotExist as exc:
        raise NotFound() from exc
    for field in ("name", "slug", "description", "is_active"):
        if field in fields:
            setattr(category, field, fields[field])
    return _category_save(category=category)


@transaction.atomic
def category_delete(*, category_id: int) -> None:
    """Функция, удаляющая категорию при отсутствии неархивных объявлений"""

    try:
        category = Category.objects.select_for_update().get(pk=category_id)
    except Category.DoesNotExist as exc:
        raise NotFound() from exc
    count = category.resources.exclude(status=ResourceStatus.ARCHIVED).count()
    if count:
        raise CategoryInUse(
            f"Category is used by {count} non-archived listing(s). "
            "Deactivate it with is_active=false."
        )
    category.delete()


def reference_create(*, reference_type: str, value: str, is_active: bool = True) -> Reference:
    """Функция, создающая значение указанного справочника"""

    reference = Reference(type=reference_type, value=value, is_active=is_active)
    reference.full_clean()
    reference.save()
    return reference


@transaction.atomic
def reference_update(*, reference_id: int, **fields: object) -> Reference:
    """Функция, изменяющая переданные свойства значения справочника"""

    try:
        reference = Reference.objects.select_for_update().get(pk=reference_id)
    except Reference.DoesNotExist as exc:
        raise NotFound() from exc
    if "reference_type" in fields:
        reference.type = fields["reference_type"]
    for field in ("value", "is_active"):
        if field in fields:
            setattr(reference, field, fields[field])
    reference.full_clean()
    reference.save()
    return reference


@transaction.atomic
def reference_delete(*, reference_id: int) -> None:
    """Функция, удаляющая значение справочника при отсутствии связей с ресурсами"""

    try:
        reference = Reference.objects.select_for_update().get(pk=reference_id)
    except Reference.DoesNotExist as exc:
        raise NotFound() from exc
    count = reference.resources.count()
    if count:
        raise ReferenceInUse(
            f"Reference is used by {count} listing(s). Deactivate it with is_active=false."
        )
    reference.delete()
