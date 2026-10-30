import logging

from django.core.exceptions import PermissionDenied as DjangoPermissionDenied
from django.http import Http404
from rest_framework.exceptions import (
    AuthenticationFailed,
    MethodNotAllowed,
    NotAuthenticated,
    NotFound,
    PermissionDenied,
    ValidationError,
)
from rest_framework.response import Response
from rest_framework.views import exception_handler

logger = logging.getLogger(__name__)


def api_exception_handler(exc: Exception, context: dict) -> Response | None:
    """Функция, приводящая ошибки API к единому формату ответа"""

    response = exception_handler(exc, context)
    if response is None:
        logger.error("Неожиданная ошибка API: %s", type(exc).__name__)
        return Response(
            {"code": "INTERNAL_ERROR", "message": "Внутренняя ошибка сервера.", "details": {}},
            status=500,
        )

    if isinstance(exc, (NotAuthenticated, AuthenticationFailed)):
        code = "UNAUTHORIZED"
        message = "Требуется авторизация."
    elif isinstance(exc, (PermissionDenied, DjangoPermissionDenied)):
        code = "ACCESS_DENIED"
        message = "Недостаточно прав для выполнения операции."
    elif isinstance(exc, ValidationError):
        code = "VALIDATION_ERROR"
        message = "Некорректные параметры запроса."
    elif isinstance(exc, (NotFound, Http404)):
        code = "NOT_FOUND"
        message = "Запрошенный объект не найден."
    elif isinstance(exc, MethodNotAllowed):
        code = "METHOD_NOT_ALLOWED"
        message = "Метод запроса не поддерживается."
    else:
        code = "API_ERROR"
        message = "Не удалось обработать запрос."

    details = {}
    if isinstance(exc, ValidationError):
        details = (
            response.data
            if isinstance(response.data, dict)
            else {"non_field_errors": response.data}
        )
    response.data = {"code": code, "message": message, "details": details}
    return response
