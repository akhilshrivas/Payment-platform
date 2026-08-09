"""
Custom DRF exception handler.

Returns a consistent JSON envelope:
  {
      "success": false,
      "message": "Human-readable description",
      "errors": { ... }   (optional detail)
  }

Never exposes internal stack traces in production.
"""

import logging

from django.core.exceptions import PermissionDenied, ValidationError
from django.http import Http404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler

logger = logging.getLogger(__name__)

# Mapping of DRF status codes to friendly messages
_STATUS_MESSAGES: dict[int, str] = {
    status.HTTP_400_BAD_REQUEST: "Bad request. Please check your input.",
    status.HTTP_401_UNAUTHORIZED: "Authentication credentials were not provided or are invalid.",
    status.HTTP_403_FORBIDDEN: "You do not have permission to perform this action.",
    status.HTTP_404_NOT_FOUND: "The requested resource was not found.",
    status.HTTP_405_METHOD_NOT_ALLOWED: "HTTP method not allowed.",
    status.HTTP_409_CONFLICT: "Conflict with the current state of the resource.",
    status.HTTP_422_UNPROCESSABLE_ENTITY: "Unprocessable entity.",
    status.HTTP_429_TOO_MANY_REQUESTS: "Too many requests. Please slow down.",
    status.HTTP_500_INTERNAL_SERVER_ERROR: "An internal server error occurred.",
}


def custom_exception_handler(exc: Exception, context: dict) -> Response | None:
    """
    Custom exception handler that wraps all error responses in a
    consistent { success, message, errors } envelope.
    """
    # Let DRF handle the response first
    response = exception_handler(exc, context)

    if response is not None:
        status_code = response.status_code
        default_message = _STATUS_MESSAGES.get(status_code, "An error occurred.")

        # Extract message/errors from the DRF response data
        data = response.data
        errors: dict = {}
        message: str = default_message

        if isinstance(data, dict):
            # DRF often uses 'detail' for message-level errors
            if "detail" in data:
                message = str(data.pop("detail"))
            errors = data
        elif isinstance(data, list):
            errors = {"non_field_errors": data}
        elif isinstance(data, str):
            message = data

        response.data = {
            "success": False,
            "message": message,
            "errors": errors,
        }
        return response

    # Handle Django-native exceptions not caught by DRF
    if isinstance(exc, Http404):
        return Response(
            {"success": False, "message": "Resource not found.", "errors": {}},
            status=status.HTTP_404_NOT_FOUND,
        )

    if isinstance(exc, PermissionDenied):
        return Response(
            {"success": False, "message": "Permission denied.", "errors": {}},
            status=status.HTTP_403_FORBIDDEN,
        )

    if isinstance(exc, ValidationError):
        return Response(
            {"success": False, "message": "Validation error.", "errors": exc.message_dict if hasattr(exc, "message_dict") else {"error": str(exc)}},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Unhandled — log it and return 500
    logger.exception("Unhandled exception in view: %s", exc)
    return Response(
        {"success": False, "message": "An unexpected error occurred.", "errors": {}},
        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )


class ApplicationError(Exception):
    """
    Base class for domain-level application errors.
    Views can catch this and return an appropriate HTTP response.
    """

    def __init__(self, message: str, code: int = status.HTTP_400_BAD_REQUEST) -> None:
        self.message = message
        self.code = code
        super().__init__(message)


class InsufficientBalanceError(ApplicationError):
    """Raised when a wallet does not have enough available balance."""

    def __init__(self, message: str = "Insufficient wallet balance.") -> None:
        super().__init__(message, code=status.HTTP_400_BAD_REQUEST)


class DuplicateTransactionError(ApplicationError):
    """Raised when a transaction with the same reference already exists."""

    def __init__(self, message: str = "Duplicate transaction detected.") -> None:
        super().__init__(message, code=status.HTTP_409_CONFLICT)


class PaymentNotFoundError(ApplicationError):
    """Raised when a payment record cannot be located."""

    def __init__(self, message: str = "Payment not found.") -> None:
        super().__init__(message, code=status.HTTP_404_NOT_FOUND)


class WebhookVerificationError(ApplicationError):
    """Raised when a webhook signature fails verification."""

    def __init__(self, message: str = "Webhook signature verification failed.") -> None:
        super().__init__(message, code=status.HTTP_400_BAD_REQUEST)
