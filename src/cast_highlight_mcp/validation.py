"""Input validation for MCP tool arguments.

This module provides validation functions for tool arguments to ensure
type safety and valid value ranges before processing API requests.
"""

from dataclasses import dataclass
from typing import Any


class ValidationError(Exception):
    """Raised when input validation fails.

    Attributes:
        field: The name of the field that failed validation
        message: A human-readable error message
    """

    def __init__(self, field: str, message: str):
        self.field = field
        self.message = message
        super().__init__(f"Validation error for '{field}': {message}")


@dataclass
class ValidatedCompanyArgs:
    """Container for validated company-related arguments.

    Used by tools that only need an optional company_id.
    """

    company_id: int | None = None


@dataclass
class ValidatedDomainArgs:
    """Container for validated domain-related arguments.

    Used by tools that require a domain_id.
    """

    domain_id: int


@dataclass
class ValidatedApplicationArgs:
    """Container for validated application-related arguments.

    Used by tools that require both a domain_id and an application_id,
    since all per-application API endpoints are nested under domains.
    """

    domain_id: int
    application_id: int


def validate_positive_integer(value: Any, field_name: str, required: bool = False) -> int | None:
    """Validate that a value is a positive integer.

    Args:
        value: The value to validate
        field_name: Name of the field (for error messages)
        required: Whether the field is required

    Returns:
        The validated integer or None if not provided and not required

    Raises:
        ValidationError: If validation fails
    """
    if value is None:
        if required:
            raise ValidationError(field_name, "is required but was not provided")
        return None

    # Handle string values that might be numeric
    if isinstance(value, str):
        try:
            value = int(value)
        except ValueError:
            raise ValidationError(field_name, "must be a valid integer")

    if not isinstance(value, int):
        raise ValidationError(field_name, "must be an integer")

    # Check for boolean (which is a subclass of int in Python)
    if isinstance(value, bool):
        raise ValidationError(field_name, "must be an integer")

    if value <= 0:
        raise ValidationError(field_name, "must be a positive integer")

    # Check for reasonable upper bound (prevent potential overflow/abuse)
    max_id = 2**31 - 1  # Max 32-bit signed integer
    if value > max_id:
        raise ValidationError(field_name, f"exceeds maximum allowed value ({max_id})")

    return value


def validate_company_id(arguments: dict, required: bool = False) -> int | None:
    """Validate company_id argument.

    Args:
        arguments: The tool arguments dictionary
        required: Whether company_id is required

    Returns:
        Validated company_id or None

    Raises:
        ValidationError: If validation fails
    """
    return validate_positive_integer(arguments.get("company_id"), "company_id", required)


def validate_domain_id(arguments: dict, required: bool = True) -> int | None:
    """Validate domain_id argument.

    Args:
        arguments: The tool arguments dictionary
        required: Whether domain_id is required (default True)

    Returns:
        Validated domain_id or None

    Raises:
        ValidationError: If validation fails
    """
    return validate_positive_integer(arguments.get("domain_id"), "domain_id", required)


def validate_application_id(arguments: dict, required: bool = True) -> int | None:
    """Validate application_id argument.

    Args:
        arguments: The tool arguments dictionary
        required: Whether application_id is required (default True)

    Returns:
        Validated application_id or None

    Raises:
        ValidationError: If validation fails
    """
    return validate_positive_integer(arguments.get("application_id"), "application_id", required)


def validate_get_company_args(arguments: dict) -> ValidatedCompanyArgs:
    """Validate arguments for highlight_get_company tool.

    Args:
        arguments: The tool arguments dictionary

    Returns:
        ValidatedCompanyArgs with validated company_id

    Raises:
        ValidationError: If validation fails
    """
    return ValidatedCompanyArgs(company_id=validate_company_id(arguments, required=False))


def validate_list_domains_args(arguments: dict) -> ValidatedCompanyArgs:
    """Validate arguments for highlight_list_domains tool.

    Args:
        arguments: The tool arguments dictionary

    Returns:
        ValidatedCompanyArgs with validated company_id

    Raises:
        ValidationError: If validation fails
    """
    return ValidatedCompanyArgs(company_id=validate_company_id(arguments, required=False))


def validate_get_domain_args(arguments: dict) -> ValidatedDomainArgs:
    """Validate arguments for highlight_get_domain tool.

    Args:
        arguments: The tool arguments dictionary

    Returns:
        ValidatedDomainArgs with validated domain_id

    Raises:
        ValidationError: If validation fails
    """
    domain_id = validate_domain_id(arguments, required=True)
    assert domain_id is not None  # Required validation ensures this
    return ValidatedDomainArgs(domain_id=domain_id)


def validate_list_applications_args(arguments: dict) -> ValidatedDomainArgs:
    """Validate arguments for highlight_list_applications tool.

    Args:
        arguments: The tool arguments dictionary

    Returns:
        ValidatedDomainArgs with validated domain_id

    Raises:
        ValidationError: If validation fails
    """
    domain_id = validate_domain_id(arguments, required=True)
    assert domain_id is not None  # Required validation ensures this
    return ValidatedDomainArgs(domain_id=domain_id)


def validate_application_args(arguments: dict) -> ValidatedApplicationArgs:
    """Validate arguments for application-related tools.

    This is used by highlight_get_application, highlight_get_metrics,
    highlight_get_technologies, highlight_get_cloud_readiness,
    and highlight_get_third_parties tools.

    Args:
        arguments: The tool arguments dictionary

    Returns:
        ValidatedApplicationArgs with validated domain_id and application_id

    Raises:
        ValidationError: If validation fails
    """
    domain_id = validate_domain_id(arguments, required=True)
    assert domain_id is not None  # Required validation ensures this
    application_id = validate_application_id(arguments, required=True)
    assert application_id is not None  # Required validation ensures this
    return ValidatedApplicationArgs(domain_id=domain_id, application_id=application_id)
