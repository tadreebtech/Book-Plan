from rest_framework.exceptions import APIException


class BookingValidationError(APIException):
    status_code = 400
    default_detail = "Invalid booking data."
    default_code = "INVALID_BOOKING"


class ResourceUnavailable(APIException):
    status_code = 400
    default_detail = "Resource is unavailable for booking."
    default_code = "RESOURCE_UNAVAILABLE"


class BookingConflict(APIException):
    status_code = 409
    default_detail = "This time slot is already booked."
    default_code = "BOOKING_CONFLICT"
