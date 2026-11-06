import logging
from typing import Any

from django.core.exceptions import ValidationError as DjangoValidationError
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.views.defaults import page_not_found
from rest_framework import exceptions
from rest_framework.response import Response
from rest_framework.serializers import as_serializer_error
from rest_framework.views import exception_handler

logger = logging.getLogger(__name__)


class ApplicationError(Exception):
    """Класс, описывающий ожидаемую ошибку бизнес-правила с кодом и HTTP-статусом ответа"""

    status_code = 400
    code = "APPLICATION_ERROR"
    message = "The request cannot be processed."

    def __init__(self, message: str | None = None, *, details: dict | None = None) -> None:
        """Метод, сохраняющий текст ошибки и дополнительные сведения о ней"""
        self.message = message or self.message
        self.details = details or {}
        super().__init__(self.message)


def error_body(*, code: str, message: str, details: Any = None) -> dict:
    """Функция, собирающая тело ответа об ошибке в едином формате API"""
    return {"code": code, "message": message, "details": details or {}}


def custom_exception_handler(exc: Exception, context: dict) -> Response | None:
    """Функция, превращающая ошибку запроса API в ответ формата code, message, details"""
    if isinstance(exc, ApplicationError):
        return Response(
            error_body(code=exc.code, message=exc.message, details=exc.details),
            status=exc.status_code,
        )

    if isinstance(exc, DjangoValidationError):
        exc = exceptions.ValidationError(as_serializer_error(exc))

    response = exception_handler(exc, context)
    if response is None:
        logger.exception("Unexpected API error", exc_info=exc)
        return None

    if isinstance(exc, exceptions.ValidationError):
        response.data = error_body(
            code="VALIDATION_ERROR", message="Invalid request data.", details=response.data
        )
        return response

    codes = exc.get_codes() if isinstance(exc, exceptions.APIException) else None
    code = codes.upper() if isinstance(codes, str) else "API_ERROR"
    message = str(response.data.get("detail", "")) if isinstance(response.data, dict) else ""
    response.data = error_body(code=code, message=message)
    return response


def page_not_found_handler(request: HttpRequest, exception: Exception) -> HttpResponse:
    """Функция, отвечающая на неизвестный адрес API ошибкой NOT_FOUND, на остальные стандартно"""
    if request.path.startswith("/api/"):
        return JsonResponse(error_body(code="NOT_FOUND", message="Not found."), status=404)
    return page_not_found(request, exception)
