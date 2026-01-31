"""Tests for input validation module."""

import pytest

from cast_highlight_mcp.validation import (
    ValidatedApplicationArgs,
    ValidatedCompanyArgs,
    ValidatedDomainArgs,
    ValidationError,
    validate_application_args,
    validate_application_id,
    validate_company_id,
    validate_domain_id,
    validate_get_company_args,
    validate_get_domain_args,
    validate_list_applications_args,
    validate_list_domains_args,
    validate_positive_integer,
)


class TestValidationError:
    """Tests for ValidationError exception."""

    def test_validation_error_attributes(self):
        """Test ValidationError has correct attributes."""
        error = ValidationError("test_field", "test message")
        assert error.field == "test_field"
        assert error.message == "test message"

    def test_validation_error_str(self):
        """Test ValidationError string representation."""
        error = ValidationError("company_id", "must be positive")
        assert str(error) == "Validation error for 'company_id': must be positive"


class TestValidatePositiveInteger:
    """Tests for validate_positive_integer function."""

    def test_valid_positive_integer(self):
        """Test valid positive integer passes validation."""
        assert validate_positive_integer(42, "test_field") == 42
        assert validate_positive_integer(1, "test_field") == 1
        assert validate_positive_integer(999999, "test_field") == 999999

    def test_none_when_not_required(self):
        """Test None is accepted when field is not required."""
        assert validate_positive_integer(None, "test_field", required=False) is None

    def test_none_when_required_raises(self):
        """Test None raises ValidationError when field is required."""
        with pytest.raises(ValidationError) as exc_info:
            validate_positive_integer(None, "test_field", required=True)
        assert exc_info.value.field == "test_field"
        assert "required" in exc_info.value.message

    def test_zero_raises_error(self):
        """Test zero is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            validate_positive_integer(0, "test_field")
        assert exc_info.value.field == "test_field"
        assert "positive" in exc_info.value.message

    def test_negative_integer_raises_error(self):
        """Test negative integers are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            validate_positive_integer(-1, "test_field")
        assert exc_info.value.field == "test_field"
        assert "positive" in exc_info.value.message

    def test_string_integer_is_converted(self):
        """Test string integers are converted to int."""
        assert validate_positive_integer("123", "test_field") == 123
        assert validate_positive_integer("1", "test_field") == 1

    def test_non_numeric_string_raises_error(self):
        """Test non-numeric strings are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            validate_positive_integer("abc", "test_field")
        assert exc_info.value.field == "test_field"
        assert "must be an integer" in exc_info.value.message

    def test_float_raises_error(self):
        """Test floats are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            validate_positive_integer(3.14, "test_field")
        assert exc_info.value.field == "test_field"
        assert "must be an integer" in exc_info.value.message

    def test_boolean_raises_error(self):
        """Test booleans are rejected (even though bool is int subclass)."""
        with pytest.raises(ValidationError) as exc_info:
            validate_positive_integer(True, "test_field")
        assert exc_info.value.field == "test_field"
        assert "boolean" in exc_info.value.message

        with pytest.raises(ValidationError) as exc_info:
            validate_positive_integer(False, "test_field")
        assert "boolean" in exc_info.value.message

    def test_list_raises_error(self):
        """Test lists are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            validate_positive_integer([1, 2, 3], "test_field")
        assert exc_info.value.field == "test_field"
        assert "must be an integer" in exc_info.value.message

    def test_dict_raises_error(self):
        """Test dicts are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            validate_positive_integer({"id": 1}, "test_field")
        assert exc_info.value.field == "test_field"
        assert "must be an integer" in exc_info.value.message

    def test_max_value_boundary(self):
        """Test maximum value boundary."""
        max_val = 2**31 - 1
        # At boundary - should pass
        assert validate_positive_integer(max_val, "test_field") == max_val

        # Over boundary - should fail
        with pytest.raises(ValidationError) as exc_info:
            validate_positive_integer(max_val + 1, "test_field")
        assert "exceeds maximum" in exc_info.value.message


class TestValidateCompanyId:
    """Tests for validate_company_id function."""

    def test_valid_company_id(self):
        """Test valid company_id passes."""
        assert validate_company_id({"company_id": 1234}) == 1234

    def test_missing_company_id_when_not_required(self):
        """Test missing company_id returns None when not required."""
        assert validate_company_id({}, required=False) is None
        assert validate_company_id({"other": "value"}, required=False) is None

    def test_missing_company_id_when_required_raises(self):
        """Test missing company_id raises when required."""
        with pytest.raises(ValidationError) as exc_info:
            validate_company_id({}, required=True)
        assert exc_info.value.field == "company_id"

    def test_invalid_company_id_raises(self):
        """Test invalid company_id raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            validate_company_id({"company_id": -1})
        assert exc_info.value.field == "company_id"


class TestValidateDomainId:
    """Tests for validate_domain_id function."""

    def test_valid_domain_id(self):
        """Test valid domain_id passes."""
        assert validate_domain_id({"domain_id": 5678}) == 5678

    def test_missing_domain_id_when_required_raises(self):
        """Test missing domain_id raises when required (default)."""
        with pytest.raises(ValidationError) as exc_info:
            validate_domain_id({})
        assert exc_info.value.field == "domain_id"
        assert "required" in exc_info.value.message

    def test_missing_domain_id_when_not_required(self):
        """Test missing domain_id returns None when not required."""
        assert validate_domain_id({}, required=False) is None

    def test_invalid_domain_id_raises(self):
        """Test invalid domain_id raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            validate_domain_id({"domain_id": 0})
        assert exc_info.value.field == "domain_id"


class TestValidateApplicationId:
    """Tests for validate_application_id function."""

    def test_valid_application_id(self):
        """Test valid application_id passes."""
        assert validate_application_id({"application_id": 9999}) == 9999

    def test_missing_application_id_when_required_raises(self):
        """Test missing application_id raises when required (default)."""
        with pytest.raises(ValidationError) as exc_info:
            validate_application_id({})
        assert exc_info.value.field == "application_id"
        assert "required" in exc_info.value.message

    def test_missing_application_id_when_not_required(self):
        """Test missing application_id returns None when not required."""
        assert validate_application_id({}, required=False) is None

    def test_invalid_application_id_raises(self):
        """Test invalid application_id raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            validate_application_id({"application_id": "invalid"})
        assert exc_info.value.field == "application_id"


class TestValidateGetCompanyArgs:
    """Tests for validate_get_company_args function."""

    def test_empty_args_returns_none_company_id(self):
        """Test empty arguments returns ValidatedCompanyArgs with None company_id."""
        result = validate_get_company_args({})
        assert isinstance(result, ValidatedCompanyArgs)
        assert result.company_id is None

    def test_valid_company_id(self):
        """Test valid company_id is captured."""
        result = validate_get_company_args({"company_id": 1234})
        assert result.company_id == 1234

    def test_invalid_company_id_raises(self):
        """Test invalid company_id raises ValidationError."""
        with pytest.raises(ValidationError):
            validate_get_company_args({"company_id": -1})


class TestValidateListDomainsArgs:
    """Tests for validate_list_domains_args function."""

    def test_empty_args_returns_none_company_id(self):
        """Test empty arguments returns ValidatedCompanyArgs with None company_id."""
        result = validate_list_domains_args({})
        assert isinstance(result, ValidatedCompanyArgs)
        assert result.company_id is None

    def test_valid_company_id(self):
        """Test valid company_id is captured."""
        result = validate_list_domains_args({"company_id": 5678})
        assert result.company_id == 5678


class TestValidateGetDomainArgs:
    """Tests for validate_get_domain_args function."""

    def test_valid_domain_id(self):
        """Test valid domain_id is captured."""
        result = validate_get_domain_args({"domain_id": 123})
        assert isinstance(result, ValidatedDomainArgs)
        assert result.domain_id == 123

    def test_missing_domain_id_raises(self):
        """Test missing domain_id raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            validate_get_domain_args({})
        assert exc_info.value.field == "domain_id"

    def test_invalid_domain_id_raises(self):
        """Test invalid domain_id raises ValidationError."""
        with pytest.raises(ValidationError):
            validate_get_domain_args({"domain_id": 0})


class TestValidateListApplicationsArgs:
    """Tests for validate_list_applications_args function."""

    def test_valid_domain_id(self):
        """Test valid domain_id is captured."""
        result = validate_list_applications_args({"domain_id": 456})
        assert isinstance(result, ValidatedDomainArgs)
        assert result.domain_id == 456

    def test_missing_domain_id_raises(self):
        """Test missing domain_id raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            validate_list_applications_args({})
        assert exc_info.value.field == "domain_id"


class TestValidateApplicationArgs:
    """Tests for validate_application_args function."""

    def test_valid_application_id(self):
        """Test valid application_id is captured."""
        result = validate_application_args({"application_id": 789})
        assert isinstance(result, ValidatedApplicationArgs)
        assert result.application_id == 789

    def test_missing_application_id_raises(self):
        """Test missing application_id raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            validate_application_args({})
        assert exc_info.value.field == "application_id"

    def test_invalid_application_id_raises(self):
        """Test invalid application_id raises ValidationError."""
        with pytest.raises(ValidationError):
            validate_application_args({"application_id": -100})


class TestValidatedCompanyArgs:
    """Tests for ValidatedCompanyArgs dataclass."""

    def test_default_values(self):
        """Test default value is None."""
        args = ValidatedCompanyArgs()
        assert args.company_id is None

    def test_explicit_value(self):
        """Test explicit value is captured."""
        args = ValidatedCompanyArgs(company_id=1234)
        assert args.company_id == 1234


class TestValidatedDomainArgs:
    """Tests for ValidatedDomainArgs dataclass."""

    def test_explicit_value(self):
        """Test explicit value is captured."""
        args = ValidatedDomainArgs(domain_id=5678)
        assert args.domain_id == 5678


class TestValidatedApplicationArgs:
    """Tests for ValidatedApplicationArgs dataclass."""

    def test_explicit_value(self):
        """Test explicit value is captured."""
        args = ValidatedApplicationArgs(application_id=9012)
        assert args.application_id == 9012
