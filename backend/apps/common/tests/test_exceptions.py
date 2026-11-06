import json
import logging

from django.core.exceptions import ValidationError
from django.test import RequestFactory

from apps.common.exceptions import (
    ApplicationError,
    custom_exception_handler,
    page_not_found_handler,
)


class SampleError(ApplicationError):
    status_code = 409
    code = "SAMPLE_ERROR"
    message = "Sample message."


def test_application_error_uses_its_code_and_status():
    response = custom_exception_handler(SampleError(details={"field": "value"}), {})

    assert response.status_code == 409
    assert response.data == {
        "code": "SAMPLE_ERROR",
        "message": "Sample message.",
        "details": {"field": "value"},
    }


def test_django_validation_error_becomes_validation_error():
    response = custom_exception_handler(ValidationError({"guests": ["Too few."]}), {})

    assert response.status_code == 400
    assert response.data["code"] == "VALIDATION_ERROR"
    assert response.data["details"] == {"guests": ["Too few."]}


def test_unexpected_error_is_logged_and_left_to_django(caplog):
    with caplog.at_level(logging.ERROR, logger="apps.common.exceptions"):
        response = custom_exception_handler(RuntimeError("boom"), {})

    assert response is None
    assert "Unexpected API error" in caplog.text


def test_unknown_api_path_returns_not_found_json():
    request = RequestFactory().get("/api/v1/unknown/")

    response = page_not_found_handler(request, Exception())

    assert response.status_code == 404
    assert json.loads(response.content)["code"] == "NOT_FOUND"


def test_unknown_site_path_returns_django_page():
    request = RequestFactory().get("/unknown/")

    response = page_not_found_handler(request, Exception())

    assert response.status_code == 404
    assert response["Content-Type"].startswith("text/html")
