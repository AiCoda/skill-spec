"""
String Constraint Validation.

Validates string constraints defined in input specifications, including:
- min_length / max_length
- pattern (regex)
- enum (allowed values)
- format (predefined formats like email, url, etc.)
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Pattern, Set
from urllib.parse import urlparse


@dataclass
class ConstraintViolation:
    """Represents a constraint violation."""

    constraint_type: str
    field_path: str
    message: str
    actual_value: Optional[str] = None
    expected_value: Optional[str] = None
    severity: str = "error"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "constraint_type": self.constraint_type,
            "field_path": self.field_path,
            "message": self.message,
            "actual_value": self.actual_value,
            "expected_value": self.expected_value,
            "severity": self.severity,
        }


@dataclass
class ConstraintValidationResult:
    """Result of constraint validation."""

    valid: bool
    violations: List[ConstraintViolation] = field(default_factory=list)
    constraints_checked: int = 0

    def add_violation(
        self,
        constraint_type: str,
        field_path: str,
        message: str,
        actual_value: Optional[str] = None,
        expected_value: Optional[str] = None,
        severity: str = "error",
    ) -> None:
        """Add a constraint violation."""
        self.violations.append(ConstraintViolation(
            constraint_type=constraint_type,
            field_path=field_path,
            message=message,
            actual_value=actual_value,
            expected_value=expected_value,
            severity=severity,
        ))
        if severity == "error":
            self.valid = False

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "valid": self.valid,
            "violations": [v.to_dict() for v in self.violations],
            "constraints_checked": self.constraints_checked,
        }


# Predefined format validators
FORMAT_VALIDATORS = {
    "email": re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'),
    "url": re.compile(r'^https?://[^\s/$.?#].[^\s]*$'),
    "uri": re.compile(r'^[a-zA-Z][a-zA-Z0-9+.-]*://[^\s]*$'),
    "uuid": re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', re.I),
    "date": re.compile(r'^\d{4}-\d{2}-\d{2}$'),
    "datetime": re.compile(r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}'),
    "time": re.compile(r'^\d{2}:\d{2}:\d{2}'),
    "ipv4": re.compile(r'^(\d{1,3}\.){3}\d{1,3}$'),
    "ipv6": re.compile(r'^([0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}$'),
    "hostname": re.compile(r'^[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z]{2,})+$'),
    "semver": re.compile(r'^v?\d+\.\d+\.\d+(-[a-zA-Z0-9.]+)?(\+[a-zA-Z0-9.]+)?$'),
    "slug": re.compile(r'^[a-z0-9]+(-[a-z0-9]+)*$'),
    "kebab-case": re.compile(r'^[a-z0-9]+(-[a-z0-9]+)*$'),
    "snake_case": re.compile(r'^[a-z0-9]+(_[a-z0-9]+)*$'),
    "PascalCase": re.compile(r'^[A-Z][a-zA-Z0-9]*$'),
    "camelCase": re.compile(r'^[a-z][a-zA-Z0-9]*$'),
    "json-path": re.compile(r'^\$(\.[a-zA-Z_][a-zA-Z0-9_]*|\[\d+\])*$'),
    "file-path": re.compile(r'^[a-zA-Z0-9_./-]+$'),
}


class StringConstraintValidator:
    """
    Validates string constraints defined in input specifications.

    Supports:
    - min_length: Minimum string length
    - max_length: Maximum string length
    - pattern: Regex pattern to match
    - enum: List of allowed values
    - format: Predefined format (email, url, etc.)
    """

    def __init__(self, custom_formats: Optional[Dict[str, Pattern]] = None):
        """
        Initialize the validator.

        Args:
            custom_formats: Additional format validators to register.
        """
        self.formats = dict(FORMAT_VALIDATORS)
        if custom_formats:
            self.formats.update(custom_formats)

    def validate_input_constraints(
        self,
        input_def: Dict[str, Any],
        sample_value: Optional[str] = None,
    ) -> ConstraintValidationResult:
        """
        Validate constraints on a single input definition.

        Args:
            input_def: Input definition with constraints.
            sample_value: Optional sample value to validate against constraints.

        Returns:
            ConstraintValidationResult with validation status.
        """
        result = ConstraintValidationResult(valid=True)

        input_name = input_def.get("name", "unknown")
        input_type = input_def.get("type", "string")
        constraints = input_def.get("constraints", {})

        # Only validate string type constraints
        if input_type != "string":
            return result

        # Validate constraint definitions themselves
        self._validate_constraint_definitions(
            constraints, f"inputs.{input_name}", result
        )

        # If sample value provided, validate it against constraints
        if sample_value is not None:
            self._validate_value_against_constraints(
                sample_value, constraints, f"inputs.{input_name}", result
            )

        return result

    def validate_all_inputs(
        self,
        spec_data: Dict[str, Any],
    ) -> ConstraintValidationResult:
        """
        Validate all input constraints in a spec.

        Args:
            spec_data: Full specification data.

        Returns:
            ConstraintValidationResult with all validation results.
        """
        result = ConstraintValidationResult(valid=True)

        inputs = spec_data.get("inputs", [])
        for idx, input_def in enumerate(inputs):
            input_result = self.validate_input_constraints(input_def)
            result.violations.extend(input_result.violations)
            result.constraints_checked += input_result.constraints_checked

        result.valid = len([v for v in result.violations if v.severity == "error"]) == 0
        return result

    def _validate_constraint_definitions(
        self,
        constraints: Dict[str, Any],
        field_path: str,
        result: ConstraintValidationResult,
    ) -> None:
        """Validate that constraint definitions are well-formed."""
        # Check min_length
        if "min_length" in constraints:
            result.constraints_checked += 1
            min_len = constraints["min_length"]
            if not isinstance(min_len, int) or min_len < 0:
                result.add_violation(
                    constraint_type="min_length",
                    field_path=f"{field_path}.constraints.min_length",
                    message="min_length must be a non-negative integer",
                    actual_value=str(min_len),
                )

        # Check max_length
        if "max_length" in constraints:
            result.constraints_checked += 1
            max_len = constraints["max_length"]
            if not isinstance(max_len, int) or max_len < 0:
                result.add_violation(
                    constraint_type="max_length",
                    field_path=f"{field_path}.constraints.max_length",
                    message="max_length must be a non-negative integer",
                    actual_value=str(max_len),
                )

        # Check min_length <= max_length
        if "min_length" in constraints and "max_length" in constraints:
            min_len = constraints.get("min_length", 0)
            max_len = constraints.get("max_length", float("inf"))
            if isinstance(min_len, int) and isinstance(max_len, int) and min_len > max_len:
                result.add_violation(
                    constraint_type="length_range",
                    field_path=f"{field_path}.constraints",
                    message="min_length cannot be greater than max_length",
                    actual_value=f"min={min_len}, max={max_len}",
                )

        # Check pattern
        if "pattern" in constraints:
            result.constraints_checked += 1
            pattern = constraints["pattern"]
            try:
                re.compile(pattern)
            except re.error as e:
                result.add_violation(
                    constraint_type="pattern",
                    field_path=f"{field_path}.constraints.pattern",
                    message=f"Invalid regex pattern: {e}",
                    actual_value=pattern,
                )

        # Check enum
        if "enum" in constraints:
            result.constraints_checked += 1
            enum_values = constraints["enum"]
            if not isinstance(enum_values, list):
                result.add_violation(
                    constraint_type="enum",
                    field_path=f"{field_path}.constraints.enum",
                    message="enum must be a list of values",
                    actual_value=str(type(enum_values).__name__),
                )
            elif len(enum_values) == 0:
                result.add_violation(
                    constraint_type="enum",
                    field_path=f"{field_path}.constraints.enum",
                    message="enum must have at least one value",
                )

        # Check format
        if "format" in constraints:
            result.constraints_checked += 1
            format_name = constraints["format"]
            if format_name not in self.formats:
                result.add_violation(
                    constraint_type="format",
                    field_path=f"{field_path}.constraints.format",
                    message=f"Unknown format: {format_name}",
                    actual_value=format_name,
                    expected_value=", ".join(sorted(self.formats.keys())),
                    severity="warning",  # Unknown format is a warning, not error
                )

    def _validate_value_against_constraints(
        self,
        value: str,
        constraints: Dict[str, Any],
        field_path: str,
        result: ConstraintValidationResult,
    ) -> None:
        """Validate a value against constraints."""
        # Check min_length
        if "min_length" in constraints:
            min_len = constraints["min_length"]
            if isinstance(min_len, int) and len(value) < min_len:
                result.add_violation(
                    constraint_type="min_length",
                    field_path=field_path,
                    message=f"Value too short: {len(value)} < {min_len}",
                    actual_value=str(len(value)),
                    expected_value=str(min_len),
                )

        # Check max_length
        if "max_length" in constraints:
            max_len = constraints["max_length"]
            if isinstance(max_len, int) and len(value) > max_len:
                result.add_violation(
                    constraint_type="max_length",
                    field_path=field_path,
                    message=f"Value too long: {len(value)} > {max_len}",
                    actual_value=str(len(value)),
                    expected_value=str(max_len),
                )

        # Check pattern
        if "pattern" in constraints:
            pattern = constraints["pattern"]
            try:
                if not re.match(pattern, value):
                    result.add_violation(
                        constraint_type="pattern",
                        field_path=field_path,
                        message=f"Value does not match pattern: {pattern}",
                        actual_value=value,
                        expected_value=pattern,
                    )
            except re.error:
                pass  # Invalid pattern already caught above

        # Check enum
        if "enum" in constraints:
            enum_values = constraints["enum"]
            if isinstance(enum_values, list) and value not in enum_values:
                result.add_violation(
                    constraint_type="enum",
                    field_path=field_path,
                    message=f"Value not in allowed values",
                    actual_value=value,
                    expected_value=", ".join(str(v) for v in enum_values),
                )

        # Check format
        if "format" in constraints:
            format_name = constraints["format"]
            if format_name in self.formats:
                pattern = self.formats[format_name]
                if not pattern.match(value):
                    result.add_violation(
                        constraint_type="format",
                        field_path=field_path,
                        message=f"Value does not match format '{format_name}'",
                        actual_value=value,
                        expected_value=format_name,
                    )

    def register_format(self, name: str, pattern: str) -> None:
        """
        Register a custom format validator.

        Args:
            name: Format name.
            pattern: Regex pattern for validation.
        """
        self.formats[name] = re.compile(pattern)

    def list_formats(self) -> List[str]:
        """List all available format validators."""
        return sorted(self.formats.keys())


def validate_constraints(
    spec_data: Dict[str, Any],
    custom_formats: Optional[Dict[str, Pattern]] = None,
) -> ConstraintValidationResult:
    """
    Convenience function to validate all constraints in a spec.

    Args:
        spec_data: Full specification data.
        custom_formats: Optional custom format validators.

    Returns:
        ConstraintValidationResult with all validation results.
    """
    validator = StringConstraintValidator(custom_formats)
    return validator.validate_all_inputs(spec_data)


def validate_input_value(
    input_def: Dict[str, Any],
    value: str,
    custom_formats: Optional[Dict[str, Pattern]] = None,
) -> ConstraintValidationResult:
    """
    Validate a value against an input definition's constraints.

    Args:
        input_def: Input definition with constraints.
        value: Value to validate.
        custom_formats: Optional custom format validators.

    Returns:
        ConstraintValidationResult with validation status.
    """
    validator = StringConstraintValidator(custom_formats)
    return validator.validate_input_constraints(input_def, value)
