"""
Tests for String Constraint Validation.
"""

import pytest

from backend.skillspec.validator import (
    StringConstraintValidator,
    ConstraintValidationResult,
    ConstraintViolation,
    validate_constraints,
    validate_input_value,
)


class TestConstraintValidationResult:
    """Tests for ConstraintValidationResult dataclass."""

    def test_initial_state(self):
        """Test initial state of result."""
        result = ConstraintValidationResult(valid=True)
        assert result.valid is True
        assert result.violations == []
        assert result.constraints_checked == 0

    def test_add_violation_sets_invalid(self):
        """Test that adding error violation marks result invalid."""
        result = ConstraintValidationResult(valid=True)
        result.add_violation(
            constraint_type="min_length",
            field_path="inputs.name",
            message="Value too short",
            severity="error",
        )
        assert result.valid is False
        assert len(result.violations) == 1

    def test_add_warning_keeps_valid(self):
        """Test that adding warning keeps result valid."""
        result = ConstraintValidationResult(valid=True)
        result.add_violation(
            constraint_type="format",
            field_path="inputs.name",
            message="Unknown format",
            severity="warning",
        )
        assert result.valid is True
        assert len(result.violations) == 1

    def test_to_dict(self):
        """Test conversion to dictionary."""
        result = ConstraintValidationResult(valid=True, constraints_checked=3)
        result.add_violation(
            constraint_type="pattern",
            field_path="inputs.test",
            message="Pattern mismatch",
        )
        data = result.to_dict()
        assert "valid" in data
        assert "violations" in data
        assert "constraints_checked" in data


class TestConstraintViolation:
    """Tests for ConstraintViolation dataclass."""

    def test_to_dict(self):
        """Test conversion to dictionary."""
        violation = ConstraintViolation(
            constraint_type="min_length",
            field_path="inputs.name.constraints",
            message="Value too short",
            actual_value="5",
            expected_value="10",
        )
        data = violation.to_dict()
        assert data["constraint_type"] == "min_length"
        assert data["actual_value"] == "5"


class TestStringConstraintValidator:
    """Tests for StringConstraintValidator."""

    def test_validate_min_length_constraint_definition(self):
        """Test validation of min_length constraint definition."""
        validator = StringConstraintValidator()
        input_def = {
            "name": "test_input",
            "type": "string",
            "constraints": {"min_length": 5},
        }
        result = validator.validate_input_constraints(input_def)
        assert result.valid is True
        assert result.constraints_checked == 1

    def test_invalid_min_length_definition(self):
        """Test detection of invalid min_length."""
        validator = StringConstraintValidator()
        input_def = {
            "name": "test_input",
            "type": "string",
            "constraints": {"min_length": -5},
        }
        result = validator.validate_input_constraints(input_def)
        assert result.valid is False
        assert any(v.constraint_type == "min_length" for v in result.violations)

    def test_max_length_constraint_definition(self):
        """Test validation of max_length constraint."""
        validator = StringConstraintValidator()
        input_def = {
            "name": "test_input",
            "type": "string",
            "constraints": {"max_length": 100},
        }
        result = validator.validate_input_constraints(input_def)
        assert result.valid is True

    def test_min_greater_than_max(self):
        """Test detection of min_length > max_length."""
        validator = StringConstraintValidator()
        input_def = {
            "name": "test_input",
            "type": "string",
            "constraints": {"min_length": 20, "max_length": 10},
        }
        result = validator.validate_input_constraints(input_def)
        assert result.valid is False
        assert any(v.constraint_type == "length_range" for v in result.violations)

    def test_valid_pattern_constraint(self):
        """Test validation of valid regex pattern."""
        validator = StringConstraintValidator()
        input_def = {
            "name": "test_input",
            "type": "string",
            "constraints": {"pattern": r"^[a-z]+$"},
        }
        result = validator.validate_input_constraints(input_def)
        assert result.valid is True

    def test_invalid_pattern_constraint(self):
        """Test detection of invalid regex pattern."""
        validator = StringConstraintValidator()
        input_def = {
            "name": "test_input",
            "type": "string",
            "constraints": {"pattern": r"[invalid("},
        }
        result = validator.validate_input_constraints(input_def)
        assert result.valid is False
        assert any(v.constraint_type == "pattern" for v in result.violations)

    def test_valid_enum_constraint(self):
        """Test validation of enum constraint."""
        validator = StringConstraintValidator()
        input_def = {
            "name": "status",
            "type": "string",
            "constraints": {"enum": ["pending", "active", "completed"]},
        }
        result = validator.validate_input_constraints(input_def)
        assert result.valid is True

    def test_empty_enum_constraint(self):
        """Test detection of empty enum."""
        validator = StringConstraintValidator()
        input_def = {
            "name": "status",
            "type": "string",
            "constraints": {"enum": []},
        }
        result = validator.validate_input_constraints(input_def)
        assert result.valid is False
        assert any(v.constraint_type == "enum" for v in result.violations)

    def test_known_format_constraint(self):
        """Test validation of known format."""
        validator = StringConstraintValidator()
        input_def = {
            "name": "email",
            "type": "string",
            "constraints": {"format": "email"},
        }
        result = validator.validate_input_constraints(input_def)
        assert result.valid is True

    def test_unknown_format_warning(self):
        """Test warning for unknown format."""
        validator = StringConstraintValidator()
        input_def = {
            "name": "custom",
            "type": "string",
            "constraints": {"format": "unknown_format"},
        }
        result = validator.validate_input_constraints(input_def)
        # Unknown format is a warning, not error
        assert result.valid is True
        assert any(
            v.constraint_type == "format" and v.severity == "warning"
            for v in result.violations
        )

    def test_non_string_type_skipped(self):
        """Test that non-string types are skipped."""
        validator = StringConstraintValidator()
        input_def = {
            "name": "count",
            "type": "integer",
            "constraints": {"min_length": 5},
        }
        result = validator.validate_input_constraints(input_def)
        assert result.valid is True
        assert result.constraints_checked == 0


class TestValueValidation:
    """Tests for validating actual values against constraints."""

    def test_value_too_short(self):
        """Test detection of value shorter than min_length."""
        validator = StringConstraintValidator()
        input_def = {
            "name": "test",
            "type": "string",
            "constraints": {"min_length": 10},
        }
        result = validator.validate_input_constraints(input_def, sample_value="short")
        assert result.valid is False
        assert any(
            v.message.startswith("Value too short") for v in result.violations
        )

    def test_value_too_long(self):
        """Test detection of value longer than max_length."""
        validator = StringConstraintValidator()
        input_def = {
            "name": "test",
            "type": "string",
            "constraints": {"max_length": 5},
        }
        result = validator.validate_input_constraints(input_def, sample_value="toolongvalue")
        assert result.valid is False
        assert any(
            v.message.startswith("Value too long") for v in result.violations
        )

    def test_value_matches_pattern(self):
        """Test value matching pattern."""
        validator = StringConstraintValidator()
        input_def = {
            "name": "test",
            "type": "string",
            "constraints": {"pattern": r"^[a-z]+$"},
        }
        result = validator.validate_input_constraints(input_def, sample_value="lowercase")
        assert result.valid is True

    def test_value_not_matching_pattern(self):
        """Test value not matching pattern."""
        validator = StringConstraintValidator()
        input_def = {
            "name": "test",
            "type": "string",
            "constraints": {"pattern": r"^[a-z]+$"},
        }
        result = validator.validate_input_constraints(input_def, sample_value="HAS_UPPER")
        assert result.valid is False
        assert any(
            "does not match pattern" in v.message for v in result.violations
        )

    def test_value_in_enum(self):
        """Test value in enum list."""
        validator = StringConstraintValidator()
        input_def = {
            "name": "status",
            "type": "string",
            "constraints": {"enum": ["active", "inactive"]},
        }
        result = validator.validate_input_constraints(input_def, sample_value="active")
        assert result.valid is True

    def test_value_not_in_enum(self):
        """Test value not in enum list."""
        validator = StringConstraintValidator()
        input_def = {
            "name": "status",
            "type": "string",
            "constraints": {"enum": ["active", "inactive"]},
        }
        result = validator.validate_input_constraints(input_def, sample_value="unknown")
        assert result.valid is False
        assert any(v.constraint_type == "enum" for v in result.violations)

    def test_email_format_valid(self):
        """Test valid email format."""
        validator = StringConstraintValidator()
        input_def = {
            "name": "email",
            "type": "string",
            "constraints": {"format": "email"},
        }
        result = validator.validate_input_constraints(
            input_def, sample_value="test@example.com"
        )
        assert result.valid is True

    def test_email_format_invalid(self):
        """Test invalid email format."""
        validator = StringConstraintValidator()
        input_def = {
            "name": "email",
            "type": "string",
            "constraints": {"format": "email"},
        }
        result = validator.validate_input_constraints(
            input_def, sample_value="not-an-email"
        )
        assert result.valid is False


class TestFormatValidators:
    """Tests for predefined format validators."""

    def test_url_format(self):
        """Test URL format validation."""
        validator = StringConstraintValidator()
        input_def = {
            "name": "url",
            "type": "string",
            "constraints": {"format": "url"},
        }
        # Valid URL
        result = validator.validate_input_constraints(
            input_def, sample_value="https://example.com/path"
        )
        assert result.valid is True

        # Invalid URL
        result = validator.validate_input_constraints(
            input_def, sample_value="not-a-url"
        )
        assert result.valid is False

    def test_uuid_format(self):
        """Test UUID format validation."""
        validator = StringConstraintValidator()
        input_def = {
            "name": "id",
            "type": "string",
            "constraints": {"format": "uuid"},
        }
        result = validator.validate_input_constraints(
            input_def, sample_value="550e8400-e29b-41d4-a716-446655440000"
        )
        assert result.valid is True

    def test_date_format(self):
        """Test date format validation."""
        validator = StringConstraintValidator()
        input_def = {
            "name": "date",
            "type": "string",
            "constraints": {"format": "date"},
        }
        result = validator.validate_input_constraints(
            input_def, sample_value="2024-01-15"
        )
        assert result.valid is True

    def test_semver_format(self):
        """Test semver format validation."""
        validator = StringConstraintValidator()
        input_def = {
            "name": "version",
            "type": "string",
            "constraints": {"format": "semver"},
        }
        result = validator.validate_input_constraints(
            input_def, sample_value="1.2.3"
        )
        assert result.valid is True

        result = validator.validate_input_constraints(
            input_def, sample_value="v1.0.0-beta.1"
        )
        assert result.valid is True

    def test_kebab_case_format(self):
        """Test kebab-case format validation."""
        validator = StringConstraintValidator()
        input_def = {
            "name": "slug",
            "type": "string",
            "constraints": {"format": "kebab-case"},
        }
        result = validator.validate_input_constraints(
            input_def, sample_value="my-skill-name"
        )
        assert result.valid is True

    def test_snake_case_format(self):
        """Test snake_case format validation."""
        validator = StringConstraintValidator()
        input_def = {
            "name": "var",
            "type": "string",
            "constraints": {"format": "snake_case"},
        }
        result = validator.validate_input_constraints(
            input_def, sample_value="my_variable_name"
        )
        assert result.valid is True


class TestCustomFormats:
    """Tests for custom format registration."""

    def test_register_custom_format(self):
        """Test registering a custom format."""
        import re
        custom_formats = {"custom_id": re.compile(r"^ID-\d{4}$")}
        validator = StringConstraintValidator(custom_formats=custom_formats)

        input_def = {
            "name": "id",
            "type": "string",
            "constraints": {"format": "custom_id"},
        }
        result = validator.validate_input_constraints(
            input_def, sample_value="ID-1234"
        )
        assert result.valid is True

        result = validator.validate_input_constraints(
            input_def, sample_value="invalid"
        )
        assert result.valid is False

    def test_list_formats(self):
        """Test listing available formats."""
        validator = StringConstraintValidator()
        formats = validator.list_formats()
        assert "email" in formats
        assert "url" in formats
        assert "uuid" in formats


class TestConvenienceFunctions:
    """Tests for convenience functions."""

    def test_validate_constraints(self):
        """Test validate_constraints function."""
        spec_data = {
            "inputs": [
                {
                    "name": "name",
                    "type": "string",
                    "constraints": {"min_length": 1, "max_length": 100},
                },
                {
                    "name": "email",
                    "type": "string",
                    "constraints": {"format": "email"},
                },
            ]
        }
        result = validate_constraints(spec_data)
        assert result.valid is True
        assert result.constraints_checked > 0

    def test_validate_input_value(self):
        """Test validate_input_value function."""
        input_def = {
            "name": "status",
            "type": "string",
            "constraints": {"enum": ["active", "inactive"]},
        }
        result = validate_input_value(input_def, "active")
        assert result.valid is True

        result = validate_input_value(input_def, "unknown")
        assert result.valid is False
