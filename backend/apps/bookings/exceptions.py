from apps.common.exceptions import ApplicationError


class BookingValidationError(ApplicationError):
    code = "INVALID_BOOKING"
    message = "Invalid booking data."


class CapacityExceeded(ApplicationError):
    code = "CAPACITY_EXCEEDED"
    message = "Guests exceed resource capacity."


class ResourceUnavailable(ApplicationError):
    code = "RESOURCE_UNAVAILABLE"
    message = "Resource is unavailable for booking."


class BookingNotFound(ApplicationError):
    status_code = 404
    code = "NOT_FOUND"
    message = "Booking not found."


class BookingConflict(ApplicationError):
    status_code = 409
    code = "BOOKING_CONFLICT"
    message = "This time slot is already booked."


class BookingAlreadyCancelled(ApplicationError):
    status_code = 409
    code = "ALREADY_CANCELLED"
    message = "Booking is already cancelled."


class BookingCompleted(ApplicationError):
    status_code = 409
    code = "BOOKING_COMPLETED"
    message = "Completed bookings cannot be cancelled."
