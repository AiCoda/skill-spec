"""
Tests for Skill-Spec Pydantic models.
"""

import pytest
from pydantic import ValidationError

from backend.skillspec.models import (
    SkillSpec,
    SkillMetadata,
    InputSpec,
    InputDomain,
    DecisionRule,
    ExecutionStep,
    OutputContract,
    FailureMode,
    EdgeCase,
    InputType,
    DomainType,
    OutputFormat,
)


class TestSkillMetadata:
    """Tests for SkillMetadata model."""

    def test_valid_metadata(self):
        """Test valid skill metadata."""
        metadata = SkillMetadata(
            name="extract-api-contract",
            version="1.0.0",
            purpose="Extract API contracts from source code",
            owner="platform-team"
        )
        assert metadata.name == "extract-api-contract"
        assert metadata.version == "1.0.0"

    def test_invalid_name_format(self):
        """Test invalid skill name format."""
        with pytest.raises(ValidationError) as exc_info:
            SkillMetadata(
                name="InvalidName",  # Should be kebab-case
                version="1.0.0",
                purpose="Test purpose for validation",
                owner="team"
            )
        assert "kebab-case" in str(exc_info.value)

    def test_invalid_version_format(self):
        """Test invalid version format."""
        with pytest.raises(ValidationError) as exc_info:
            SkillMetadata(
                name="valid-name",
                version="1.0",  # Should be semver
                purpose="Test purpose for validation",
                owner="team"
            )
        assert "semver" in str(exc_info.value)

    def test_purpose_too_short(self):
        """Test purpose that is too short."""
        with pytest.raises(ValidationError):
            SkillMetadata(
                name="valid-name",
                version="1.0.0",
                purpose="Short",  # Less than 10 chars
                owner="team"
            )


class TestInputSpec:
    """Tests for InputSpec model."""

    def test_valid_input_spec(self):
        """Test valid input specification."""
        input_spec = InputSpec(
            name="user_input",
            type=InputType.STRING,
            required=True,
            description="User provided input"
        )
        assert input_spec.name == "user_input"
        assert input_spec.type == InputType.STRING

    def test_input_with_domain(self):
        """Test input specification with domain."""
        input_spec = InputSpec(
            name="status",
            type=InputType.STRING,
            required=True,
            domain=InputDomain(
                type=DomainType.ENUM,
                values=["pending", "active", "completed"]
            )
        )
        assert input_spec.domain.type == DomainType.ENUM
        assert len(input_spec.domain.values) == 3

    def test_invalid_input_name(self):
        """Test invalid input name format."""
        with pytest.raises(ValidationError):
            InputSpec(
                name="Invalid-Name",  # Should be snake_case
                type=InputType.STRING,
                required=True
            )


class TestDecisionRule:
    """Tests for DecisionRule model."""

    def test_valid_rule(self):
        """Test valid decision rule."""
        rule = DecisionRule(
            id="rule_empty_input",
            priority=10,
            when="len(input) == 0",
            then={"status": "error", "code": "EMPTY_INPUT"}
        )
        assert rule.id == "rule_empty_input"
        assert rule.priority == 10

    def test_default_rule(self):
        """Test default rule."""
        rule = DecisionRule(
            id="rule_default",
            is_default=True,
            when=True,
            then={"status": "success"}
        )
        assert rule.is_default is True


class TestOutputContract:
    """Tests for OutputContract model."""

    def test_valid_contract(self):
        """Test valid output contract."""
        contract = OutputContract(
            format=OutputFormat.JSON,
            schema={
                "type": "object",
                "required": ["status"],
                "properties": {
                    "status": {"enum": ["success", "error"]}
                }
            }
        )
        assert contract.format == OutputFormat.JSON


class TestFailureMode:
    """Tests for FailureMode model."""

    def test_valid_failure_mode(self):
        """Test valid failure mode."""
        failure = FailureMode(
            code="EMPTY_INPUT",
            retryable=False,
            description="Input was empty"
        )
        assert failure.code == "EMPTY_INPUT"
        assert failure.retryable is False

    def test_invalid_code_format(self):
        """Test invalid error code format."""
        with pytest.raises(ValidationError):
            FailureMode(
                code="empty_input",  # Should be UPPER_SNAKE_CASE
                retryable=False
            )


class TestEdgeCase:
    """Tests for EdgeCase model."""

    def test_valid_edge_case(self):
        """Test valid edge case."""
        edge_case = EdgeCase(
            case="empty_input",
            expected={"status": "error", "code": "EMPTY_INPUT"}
        )
        assert edge_case.case == "empty_input"

    def test_edge_case_with_coverage_ref(self):
        """Test edge case with coverage reference."""
        edge_case = EdgeCase(
            case="validation_failure",
            expected={"status": "error"},
            covers_rule="rule_validation",
            covers_failure="VALIDATION_ERROR"
        )
        assert edge_case.covers_rule == "rule_validation"


class TestSkillSpec:
    """Tests for SkillSpec root model."""

    def test_minimal_valid_spec(self):
        """Test minimal valid skill specification."""
        spec = SkillSpec(
            skill=SkillMetadata(
                name="hello-world",
                version="1.0.0",
                purpose="Greet the user with their name",
                owner="demo-team"
            ),
            inputs=[
                InputSpec(
                    name="user_name",
                    type=InputType.STRING,
                    required=True
                )
            ],
            preconditions=["User name is provided"],
            non_goals=["Does not validate name format"],
            decision_rules=[
                DecisionRule(
                    id="greet",
                    when="len(user_name) > 0",
                    then={"action": "generate_greeting"}
                )
            ],
            steps=[
                ExecutionStep(
                    id="greet",
                    action="generate_greeting",
                    output="greeting_message"
                )
            ],
            output_contract=OutputContract(
                format=OutputFormat.TEXT,
                schema={"type": "string"}
            ),
            failure_modes=[
                FailureMode(
                    code="EMPTY_NAME",
                    retryable=False
                )
            ],
            edge_cases=[
                EdgeCase(
                    case="empty_name",
                    expected={"status": "error", "code": "EMPTY_NAME"}
                )
            ]
        )

        assert spec.skill.name == "hello-world"
        assert len(spec.inputs) == 1
        assert len(spec.edge_cases) == 1

    def test_missing_required_section(self):
        """Test that missing required sections raise error."""
        with pytest.raises(ValidationError):
            SkillSpec(
                skill=SkillMetadata(
                    name="test-skill",
                    version="1.0.0",
                    purpose="Test purpose statement",
                    owner="team"
                ),
                # Missing other required sections
            )
