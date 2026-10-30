import pytest
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

from apps.common.exceptions import api_exception_handler


@pytest.mark.parametrize(
    ("error", "code", "status"),
    [
        (NotAuthenticated(), "UNAUTHORIZED", 401),
        (AuthenticationFailed(), "UNAUTHORIZED", 401),
        (PermissionDenied(), "ACCESS_DENIED", 403),
        (ValidationError({"page": ["Invalid value"]}), "VALIDATION_ERROR", 400),
        (NotFound(), "NOT_FOUND", 404),
        (MethodNotAllowed("POST"), "METHOD_NOT_ALLOWED", 405),
        (Http404(), "NOT_FOUND", 404),
        (DjangoPermissionDenied(), "ACCESS_DENIED", 403),
    ],
)
def test_api_exception_handler_assigns_meaningful_codes(
    error: Exception, code: str, status: int
) -> None:
    """Функция, проверяющая машинные коды для ошибок DRF и Django"""

    response = api_exception_handler(error, {})

    assert response is not None
    assert response.status_code == status
    assert response.data["code"] == code
    assert set(response.data) == {"code", "message", "details"}


def test_api_exception_handler_keeps_details_as_an_object() -> None:
    """Функция, проверяющая объектный формат деталей ошибки валидации"""

    response = api_exception_handler(ValidationError(["Invalid value"]), {})

    assert response is not None
    assert response.data["code"] == "VALIDATION_ERROR"
    assert isinstance(response.data["details"], dict)
    assert "non_field_errors" in response.data["details"]


def test_api_exception_handler_hides_unexpected_error_details(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Функция, проверяющая ответ и журналирование непредвиденной ошибки без её текста"""

    response = api_exception_handler(RuntimeError("sensitive-value"), {})

    assert response is not None
    assert response.status_code == 500
    assert response.data == {
        "code": "INTERNAL_ERROR",
        "message": "Внутренняя ошибка сервера.",
        "details": {},
    }
    assert "RuntimeError" in caplog.text
    assert "sensitive-value" not in caplog.text
