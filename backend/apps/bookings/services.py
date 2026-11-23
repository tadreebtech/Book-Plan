from datetime import datetime

from django.db import IntegrityError, transaction
from django.db.models import QuerySet
from django.utils import timezone
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError

from apps.accounts.models import Role, User
from apps.bookings.exceptions import BookingConflict, BookingValidationError, ResourceUnavailable
from apps.bookings.models import (
    Booking,
    BookingStatus,
    ModerationStatus,
    Resource,
    ResourceModerationLog,
    ResourceActivationAction,
    ResourceActivationLog,
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

            if not locked_resource.is_active:
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


def _resource_moderate(
    *,
    actor: User,
    resource_id: int,
    moderation_status: ModerationStatus,
    rejection_reason: str = "",
) -> Resource:
    """Функция, атомарно сохраняющая решение модератора и запись аудита"""

    if not actor.is_active or actor.role != Role.ADMIN:
        raise PermissionDenied()

    with transaction.atomic():
        try:
            resource = Resource.objects.select_for_update().get(pk=resource_id)
        except Resource.DoesNotExist as exc:
            raise NotFound() from exc

        previous_status = resource.moderation_status
        resource.moderation_status = moderation_status
        resource.rejection_reason = rejection_reason
        resource.moderated_at = timezone.now()
        resource.moderated_by = actor
        resource.full_clean(exclude=["manager"])
        resource.save(
            update_fields=[
                "moderation_status",
                "rejection_reason",
                "moderated_at",
                "moderated_by",
                "updated_at",
            ]
        )
        audit_log = ResourceModerationLog(
            resource_id=resource.pk,
            actor=actor,
            previous_status=previous_status,
            moderation_status=moderation_status,
            rejection_reason=rejection_reason,
            created_at=resource.moderated_at,
        )
        audit_log.full_clean()
        audit_log.save()
        return resource


def resource_approve(*, actor: User, resource_id: int) -> Resource:
    """Функция, одобряющая объявление по решению администратора"""

    return _resource_moderate(
        actor=actor, resource_id=resource_id, moderation_status=ModerationStatus.APPROVED
    )


def resource_reject(*, actor: User, resource_id: int, rejection_reason: str) -> Resource:
    """Функция, отклоняющая объявление с указанием причины"""

    rejection_reason = rejection_reason.strip()
    if not rejection_reason:
        raise ValidationError({"rejection_reason": ["This field may not be blank."]})

    return _resource_moderate(
        actor=actor,
        resource_id=resource_id,
        moderation_status=ModerationStatus.REJECTED,
        rejection_reason=rejection_reason,
    )


def resource_hide(*, actor: User, resource_id: int) -> Resource:
    """Функция, скрывающая объявление по решению администратора"""

    return _resource_moderate(
        actor=actor, resource_id=resource_id, moderation_status=ModerationStatus.HIDDEN
    )


def _resource_set_active(*, actor: User, resource_id: int, is_active: bool) -> Resource:
    """Функция, атомарно меняющая активность ресурса и записывающая действие в журнал

    Брони ресурса не меняются: подтверждённые брони остаются в силе после деактивации
    """

    if not actor.is_active or actor.role != Role.ADMIN:
        raise PermissionDenied()

    with transaction.atomic():
        resource = Resource.objects.select_for_update().get(pk=resource_id)
        if resource.is_active != is_active:
            resource.is_active = is_active
            resource.save(update_fields=["is_active", "updated_at"])

            activation_log = ResourceActivationLog(
                resource_id=resource.pk,
                actor=actor,
                action=(
                    ResourceActivationAction.ACTIVATED
                    if is_active
                    else ResourceActivationAction.DEACTIVATED
                ),
            )
            activation_log.full_clean()
            activation_log.save()

        return resource


def resource_activate(*, actor: User, resource_id: int) -> Resource:
    """Функция, делающая ресурс доступным по запросу администратора"""

    return _resource_set_active(actor=actor, resource_id=resource_id, is_active=True)


def resource_deactivate(*, actor: User, resource_id: int) -> Resource:
    """Функция, снимающая ресурс с публикации по запросу администратора"""

    return _resource_set_active(actor=actor, resource_id=resource_id, is_active=False)
