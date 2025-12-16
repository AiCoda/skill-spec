"""
Enterprise Compliance Validation (Layer 5 - Optional).

Validates skill specifications against enterprise policies for:
- Security rules
- Architecture rules
- Process rules
- Regulatory rules (GDPR, etc.)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

import yaml


@dataclass
class PolicyViolation:
    """Represents a policy violation."""

    policy_id: str
    rule_id: str
    category: str
    severity: str  # error | warning | info
    description: str
    field_path: Optional[str] = None
    required_action: Optional[str] = None

    def __str__(self) -> str:
        loc = f"[{self.field_path}] " if self.field_path else ""
        return f"{loc}[{self.severity.upper()}] {self.category}/{self.rule_id}: {self.description}"


@dataclass
class ComplianceValidationResult:
    """Result of compliance validation."""

    valid: bool
    violations: List[PolicyViolation] = field(default_factory=list)
    policies_checked: List[str] = field(default_factory=list)
    category_summary: Dict[str, Dict[str, int]] = field(default_factory=dict)

    def add_violation(self, violation: PolicyViolation) -> None:
        """Add a violation and update summary."""
        self.violations.append(violation)

        # Update category summary
        if violation.category not in self.category_summary:
            self.category_summary[violation.category] = {"error": 0, "warning": 0, "info": 0}
        self.category_summary[violation.category][violation.severity] += 1

        if violation.severity == "error":
            self.valid = False

    @property
    def total_errors(self) -> int:
        return sum(1 for v in self.violations if v.severity == "error")

    @property
    def total_warnings(self) -> int:
        return sum(1 for v in self.violations if v.severity == "warning")


@dataclass
class PolicyRule:
    """A single policy rule definition."""

    id: str
    category: str
    severity: str
    description: str
    condition: Dict[str, Any]
    required_action: Optional[Dict[str, Any]] = None

    def evaluate(self, spec_data: Dict[str, Any]) -> bool:
        """
        Evaluate if this rule's condition is met.

        Returns True if the condition is satisfied (no violation).
        """
        return RuleConditionEvaluator.evaluate(self.condition, spec_data)


class RuleConditionEvaluator:
    """Evaluates policy rule conditions against spec data."""

    @staticmethod
    def evaluate(condition: Dict[str, Any], spec_data: Dict[str, Any]) -> bool:
        """
        Evaluate a condition against spec data.

        Supported conditions:
        - any_input_has_tag: Check if any input has specified tag
        - output_contains_type: Check if output contains specified type
        - uses_external_service: Check if skill uses external services
        - handles_data_type: Check if skill handles specified data type
        - has_field: Check if field exists
        - field_value_in: Check if field value is in allowed list
        """
        if not condition:
            return True

        condition_type = condition.get("type")

        if condition_type == "any_input_has_tag":
            return RuleConditionEvaluator._check_input_tags(
                spec_data, condition.get("tags", [])
            )

        if condition_type == "output_contains_type":
            return RuleConditionEvaluator._check_output_type(
                spec_data, condition.get("types", [])
            )

        if condition_type == "uses_external_service":
            return RuleConditionEvaluator._check_external_service(spec_data)

        if condition_type == "handles_data_type":
            return RuleConditionEvaluator._check_data_type(
                spec_data, condition.get("data_types", [])
            )

        if condition_type == "has_field":
            return RuleConditionEvaluator._check_has_field(
                spec_data, condition.get("path")
            )

        if condition_type == "field_value_in":
            return RuleConditionEvaluator._check_field_value(
                spec_data, condition.get("path"), condition.get("values", [])
            )

        if condition_type == "and":
            return all(
                RuleConditionEvaluator.evaluate(c, spec_data)
                for c in condition.get("conditions", [])
            )

        if condition_type == "or":
            return any(
                RuleConditionEvaluator.evaluate(c, spec_data)
                for c in condition.get("conditions", [])
            )

        if condition_type == "not":
            return not RuleConditionEvaluator.evaluate(
                condition.get("condition", {}), spec_data
            )

        # Unknown condition type, assume satisfied
        return True

    @staticmethod
    def _check_input_tags(spec_data: Dict, tags: List[str]) -> bool:
        """Check if any input has the specified tags."""
        inputs = spec_data.get("inputs", [])
        for inp in inputs:
            input_tags = inp.get("tags", [])
            if any(tag in input_tags for tag in tags):
                return True
        return False

    @staticmethod
    def _check_output_type(spec_data: Dict, types: List[str]) -> bool:
        """Check if output schema contains specified types."""
        output_contract = spec_data.get("output_contract", {})
        schema = output_contract.get("schema", {})

        def check_schema(s: Any) -> bool:
            if isinstance(s, dict):
                if s.get("type") in types:
                    return True
                for value in s.values():
                    if check_schema(value):
                        return True
            elif isinstance(s, list):
                for item in s:
                    if check_schema(item):
                        return True
            return False

        return check_schema(schema)

    @staticmethod
    def _check_external_service(spec_data: Dict) -> bool:
        """Check if skill uses external services."""
        # Check steps for external service indicators
        steps = spec_data.get("steps", [])
        external_keywords = ["api", "http", "fetch", "request", "external", "remote"]

        for step in steps:
            action = step.get("action", "").lower()
            if any(kw in action for kw in external_keywords):
                return True

        # Check context prerequisites
        context = spec_data.get("context", {})
        prerequisites = context.get("prerequisites", [])
        for prereq in prerequisites:
            prereq_lower = prereq.lower()
            if any(kw in prereq_lower for kw in ["api", "credential", "token", "key"]):
                return True

        return False

    @staticmethod
    def _check_data_type(spec_data: Dict, data_types: List[str]) -> bool:
        """Check if skill handles specified data types."""
        inputs = spec_data.get("inputs", [])
        for inp in inputs:
            tags = inp.get("tags", [])
            if any(dt in tags for dt in data_types):
                return True
            # Also check description for data type mentions
            desc = inp.get("description", "").lower()
            if any(dt.lower() in desc for dt in data_types):
                return True
        return False

    @staticmethod
    def _check_has_field(spec_data: Dict, path: str) -> bool:
        """Check if a field exists at the given path."""
        if not path:
            return False

        parts = path.split(".")
        current = spec_data

        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return False

        return current is not None

    @staticmethod
    def _check_field_value(spec_data: Dict, path: str, values: List) -> bool:
        """Check if field value is in allowed list."""
        if not path:
            return False

        parts = path.split(".")
        current = spec_data

        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return False

        return current in values


@dataclass
class Policy:
    """Enterprise policy definition."""

    id: str
    name: str
    version: str
    description: str
    extends: Optional[str] = None
    rules: List[PolicyRule] = field(default_factory=list)

    @classmethod
    def from_yaml(cls, yaml_content: str) -> "Policy":
        """Load policy from YAML content."""
        data = yaml.safe_load(yaml_content)
        policy_data = data.get("policy", {})

        rules = []
        for category, category_rules in data.items():
            if category in ("policy",):
                continue
            if isinstance(category_rules, list):
                for rule_data in category_rules:
                    rules.append(PolicyRule(
                        id=rule_data.get("id", "unknown"),
                        category=category.replace("_rules", "").upper(),
                        severity=rule_data.get("severity", "warning"),
                        description=rule_data.get("description", ""),
                        condition=rule_data.get("condition", {}),
                        required_action=rule_data.get("required_action"),
                    ))

        return cls(
            id=policy_data.get("id", "unknown"),
            name=policy_data.get("name", "Unknown Policy"),
            version=policy_data.get("version", "1.0.0"),
            description=policy_data.get("description", ""),
            extends=policy_data.get("extends"),
            rules=rules,
        )

    @classmethod
    def from_file(cls, path: Path) -> "Policy":
        """Load policy from a file."""
        with open(path, "r", encoding="utf-8") as f:
            return cls.from_yaml(f.read())


class ComplianceValidator:
    """
    Validates skill specifications against enterprise policies (Layer 5).

    Supports:
    - Multiple policy files
    - Policy inheritance (extends)
    - Severity-based aggregation
    - Category grouping
    """

    def __init__(self, policies: Optional[List[Policy]] = None):
        """
        Initialize the compliance validator.

        Args:
            policies: List of policies to validate against.
        """
        self.policies = policies or []

    def load_policy(self, path: Path) -> None:
        """Load and add a policy from file."""
        policy = Policy.from_file(path)
        self.policies.append(policy)

    def load_policies_from_dir(self, directory: Path) -> None:
        """Load all policies from a directory."""
        if not directory.exists():
            return

        for file_path in directory.glob("*.yaml"):
            try:
                self.load_policy(file_path)
            except Exception:
                pass  # Skip invalid policy files

    def validate(self, spec_data: Dict[str, Any]) -> ComplianceValidationResult:
        """
        Validate spec against all loaded policies.

        Args:
            spec_data: The specification data.

        Returns:
            ComplianceValidationResult with violations and summary.
        """
        result = ComplianceValidationResult(valid=True)

        for policy in self.policies:
            result.policies_checked.append(policy.id)
            self._validate_policy(spec_data, policy, result)

        return result

    def _validate_policy(
        self,
        spec_data: Dict[str, Any],
        policy: Policy,
        result: ComplianceValidationResult
    ) -> None:
        """Validate spec against a single policy."""
        for rule in policy.rules:
            # Check if the rule's condition applies
            condition_met = rule.evaluate(spec_data)

            if condition_met and rule.required_action:
                # Condition is met, check if required action is satisfied
                action_satisfied = self._check_required_action(
                    spec_data, rule.required_action
                )
                if not action_satisfied:
                    result.add_violation(PolicyViolation(
                        policy_id=policy.id,
                        rule_id=rule.id,
                        category=rule.category,
                        severity=rule.severity,
                        description=rule.description,
                        field_path=rule.required_action.get("path"),
                        required_action=self._format_required_action(rule.required_action),
                    ))

    def _check_required_action(
        self,
        spec_data: Dict[str, Any],
        action: Dict[str, Any]
    ) -> bool:
        """Check if a required action is satisfied."""
        action_type = action.get("type")

        if action_type == "require_field":
            path = action.get("path")
            return RuleConditionEvaluator._check_has_field(spec_data, path)

        if action_type == "require_section":
            section = action.get("section")
            return section in spec_data and spec_data[section]

        if action_type == "require_value_in":
            path = action.get("path")
            values = action.get("values", [])
            return RuleConditionEvaluator._check_field_value(spec_data, path, values)

        if action_type == "require_tag":
            tag = action.get("tag")
            inputs = spec_data.get("inputs", [])
            return any(tag in inp.get("tags", []) for inp in inputs)

        if action_type == "require_edge_case":
            case_pattern = action.get("pattern", "")
            edge_cases = spec_data.get("edge_cases", [])
            return any(case_pattern.lower() in ec.get("case", "").lower() for ec in edge_cases)

        return True

    def _format_required_action(self, action: Dict[str, Any]) -> str:
        """Format required action as human-readable string."""
        action_type = action.get("type")

        if action_type == "require_field":
            return f"Add field: {action.get('path')}"
        if action_type == "require_section":
            return f"Add section: {action.get('section')}"
        if action_type == "require_value_in":
            return f"Set {action.get('path')} to one of: {action.get('values')}"
        if action_type == "require_tag":
            return f"Add tag: {action.get('tag')}"
        if action_type == "require_edge_case":
            return f"Add edge case matching: {action.get('pattern')}"

        return str(action)
