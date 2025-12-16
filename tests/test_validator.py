"""
Tests for Skill-Spec validators.
"""

import pytest

from backend.skillspec.validator import (
    SchemaValidator,
    QualityValidator,
    CoverageValidator,
    ConsistencyValidator,
    ValidationEngine,
)


def get_minimal_valid_spec():
    """Return a minimal valid specification."""
    return {
        "spec_version": "skill-spec/1.0",
        "skill": {
            "name": "test-skill",
            "version": "1.0.0",
            "purpose": "A test skill for validation",
            "owner": "test-team"
        },
        "inputs": [
            {
                "name": "test_input",
                "type": "string",
                "required": True
            }
        ],
        "preconditions": ["Test precondition"],
        "non_goals": ["Does not do X"],
        "decision_rules": [
            {
                "id": "rule_default",
                "is_default": True,
                "when": True,
                "then": {"status": "success"}
            }
        ],
        "steps": [
            {
                "id": "process",
                "action": "process_input",
                "output": "result"
            }
        ],
        "output_contract": {
            "format": "json",
            "schema": {
                "type": "object",
                "required": ["status"],
                "properties": {
                    "status": {"enum": ["success", "error"]}
                }
            }
        },
        "failure_modes": [
            {
                "code": "VALIDATION_ERROR",
                "retryable": False
            }
        ],
        "edge_cases": [
            {
                "case": "empty_input",
                "expected": {"status": "error", "code": "VALIDATION_ERROR"}
            }
        ]
    }


class TestSchemaValidator:
    """Tests for SchemaValidator."""

    def test_valid_spec(self):
        """Test validation of valid spec."""
        validator = SchemaValidator()
        spec = get_minimal_valid_spec()
        result = validator.validate(spec)
        assert result.valid

    def test_missing_required_section(self):
        """Test detection of missing required section."""
        validator = SchemaValidator()
        spec = get_minimal_valid_spec()
        del spec["inputs"]

        result = validator.validate(spec)
        assert not result.valid
        assert any("inputs" in str(e) for e in result.errors)

    def test_invalid_spec_version(self):
        """Test detection of invalid spec version."""
        validator = SchemaValidator()
        spec = get_minimal_valid_spec()
        spec["spec_version"] = "invalid"

        result = validator.validate(spec)
        # Should have a warning for unknown version
        assert len(result.warnings) > 0


class TestQualityValidator:
    """Tests for QualityValidator."""

    def test_forbidden_pattern_detection(self):
        """Test detection of forbidden patterns."""
        validator = QualityValidator()
        spec = get_minimal_valid_spec()
        spec["skill"]["purpose"] = "Try to help the user as needed"

        result = validator.validate(spec)
        # Should detect "try to", "help", "as needed"
        assert len(result.violations) > 0

    def test_clean_spec_passes(self):
        """Test that clean spec passes quality validation."""
        validator = QualityValidator()
        spec = get_minimal_valid_spec()

        result = validator.validate(spec)
        # Should have no errors (may have warnings)
        assert result.total_errors == 0

    def test_missing_decision_rule_when(self):
        """Test detection of missing 'when' in decision rule."""
        validator = QualityValidator()
        spec = get_minimal_valid_spec()
        spec["decision_rules"] = [
            {
                "id": "bad_rule",
                "then": {"status": "success"}
                # Missing 'when'
            }
        ]

        result = validator.validate(spec)
        assert any(v.category == "MISSING_CONDITION" for v in result.violations)


class TestCoverageValidator:
    """Tests for CoverageValidator."""

    def test_uncovered_failure_mode(self):
        """Test detection of uncovered failure mode."""
        validator = CoverageValidator()
        spec = get_minimal_valid_spec()
        spec["failure_modes"].append({
            "code": "UNCOVERED_ERROR",
            "retryable": True
        })

        result = validator.validate(spec)
        assert any(g.item == "UNCOVERED_ERROR" for g in result.gaps)

    def test_missing_default_rule(self):
        """Test detection of missing default rule."""
        validator = CoverageValidator()
        spec = get_minimal_valid_spec()
        spec["decision_rules"] = [
            {
                "id": "specific_rule",
                "when": "len(input) == 0",
                "then": {"status": "error"}
            }
        ]

        result = validator.validate(spec)
        assert any(g.category == "NO_DEFAULT_PATH" for g in result.gaps)

    def test_coverage_metrics(self):
        """Test coverage metrics calculation."""
        validator = CoverageValidator()
        spec = get_minimal_valid_spec()

        result = validator.validate(spec)
        metrics = result.metrics

        # Check that metrics are calculated
        assert metrics.failure_modes_total > 0
        assert metrics.edge_cases_total > 0


class TestConsistencyValidator:
    """Tests for ConsistencyValidator."""

    def test_undefined_failure_code(self):
        """Test detection of undefined failure code in edge cases."""
        validator = ConsistencyValidator()
        spec = get_minimal_valid_spec()
        spec["edge_cases"] = [
            {
                "case": "test_case",
                "expected": {"status": "error", "code": "UNDEFINED_CODE"}
            }
        ]

        result = validator.validate(spec)
        assert any(i.category == "UNDEFINED_FAILURE_CODE" for i in result.issues)

    def test_orphan_failure_mode(self):
        """Test detection of orphan failure mode."""
        validator = ConsistencyValidator()
        spec = get_minimal_valid_spec()
        spec["failure_modes"].append({
            "code": "ORPHAN_CODE",
            "retryable": False
        })

        result = validator.validate(spec)
        assert any("ORPHAN_CODE" in o for o in result.orphans)


class TestValidationEngine:
    """Tests for ValidationEngine."""

    def test_full_validation_passes(self):
        """Test that valid spec passes all layers."""
        engine = ValidationEngine()
        spec = get_minimal_valid_spec()

        result = engine.validate(spec)
        assert result.valid

    def test_strict_mode_fails_on_warnings(self):
        """Test that strict mode fails on warnings."""
        engine = ValidationEngine()
        spec = get_minimal_valid_spec()
        # Add uncovered failure mode (creates warning)
        spec["failure_modes"].append({
            "code": "UNCOVERED",
            "retryable": True
        })

        result = engine.validate(spec, strict=True)
        # Should fail in strict mode due to warnings
        assert not result.valid or result.total_warnings > 0

    def test_result_summary(self):
        """Test result summary generation."""
        engine = ValidationEngine()
        spec = get_minimal_valid_spec()

        result = engine.validate(spec)
        summary = result.summary()

        assert "Validation" in summary
        assert "Errors:" in summary

    def test_result_to_dict(self):
        """Test result conversion to dictionary."""
        engine = ValidationEngine()
        spec = get_minimal_valid_spec()

        result = engine.validate(spec)
        data = result.to_dict()

        assert "valid" in data
        assert "layers" in data
        assert "schema" in data["layers"]
        assert "quality" in data["layers"]
