"""
Consistency Validation (Layer 4).

Validates consistency across different sections of a skill specification:
- Steps outputs match output_contract
- Failure modes match edge cases
- Cross-references are valid
- Context.works_with references exist
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set


@dataclass
class ConsistencyIssue:
    """Represents a consistency issue in the specification."""

    category: str
    source: str
    target: str
    description: str
    severity: str = "error"

    def __str__(self) -> str:
        return f"[{self.severity.upper()}] {self.category}: {self.source} -> {self.target}: {self.description}"


@dataclass
class ConsistencyValidationResult:
    """Result of consistency validation."""

    valid: bool
    issues: List[ConsistencyIssue] = field(default_factory=list)
    orphans: List[str] = field(default_factory=list)

    def add_issue(
        self,
        category: str,
        source: str,
        target: str,
        description: str,
        severity: str = "error"
    ) -> None:
        """Add a consistency issue."""
        self.issues.append(ConsistencyIssue(
            category=category,
            source=source,
            target=target,
            description=description,
            severity=severity
        ))
        if severity == "error":
            self.valid = False

    def add_orphan(self, item: str) -> None:
        """Add an orphan definition."""
        self.orphans.append(item)


class ConsistencyValidator:
    """
    Validates consistency across spec sections (Layer 4).

    Checks:
    - Steps outputs align with output_contract
    - Failure modes align with edge cases error codes
    - No orphan definitions
    - Context.works_with references valid skills (if known)
    """

    def __init__(self, known_skills: Optional[Set[str]] = None):
        """
        Initialize the consistency validator.

        Args:
            known_skills: Set of known skill names for reference validation.
        """
        self.known_skills = known_skills or set()

    def _extract_rules(self, decision_rules: Any) -> List[Dict[str, Any]]:
        """
        Extract rules from decision_rules in various formats.

        Handles three formats:
        1. List format: decision_rules is a list of rule dicts
        2. Nested format: decision_rules has _config and rules keys
        3. Dict format: decision_rules has rules as direct key-value pairs

        Args:
            decision_rules: The decision_rules section from spec data.

        Returns:
            List of rule dictionaries.
        """
        if isinstance(decision_rules, list):
            return decision_rules
        elif isinstance(decision_rules, dict):
            # Check for nested 'rules' key first (handles _config + rules format)
            if "rules" in decision_rules and isinstance(decision_rules["rules"], list):
                return decision_rules["rules"]
            # Fall back to extracting rules as direct key-value pairs
            return [
                v for k, v in decision_rules.items()
                if k != "_config" and isinstance(v, dict)
            ]
        return []

    def validate(self, spec_data: Dict[str, Any]) -> ConsistencyValidationResult:
        """
        Validate spec consistency.

        Args:
            spec_data: The specification data as a dictionary.

        Returns:
            ConsistencyValidationResult with validation status and issues.
        """
        result = ConsistencyValidationResult(valid=True)

        # Extract components
        steps = spec_data.get("steps", [])
        output_contract = spec_data.get("output_contract", {})
        failure_modes = spec_data.get("failure_modes", [])
        edge_cases = spec_data.get("edge_cases", [])
        decision_rules = spec_data.get("decision_rules", {})
        context = spec_data.get("context", {})

        # Run consistency checks
        self._check_steps_output_contract(steps, output_contract, result)
        self._check_failure_modes_edge_cases(failure_modes, edge_cases, result)
        self._check_decision_rule_references(decision_rules, failure_modes, result)
        self._check_orphan_definitions(spec_data, result)
        self._check_context_references(context, result)

        return result

    def _check_steps_output_contract(
        self,
        steps: List[Dict[str, Any]],
        output_contract: Dict[str, Any],
        result: ConsistencyValidationResult
    ) -> None:
        """Check that steps produce output matching the contract."""
        if not steps:
            return

        # Get the last step's output (should align with contract)
        last_step = steps[-1]
        last_output = last_step.get("output")

        if not last_output:
            result.add_issue(
                category="MISSING_FINAL_OUTPUT",
                source=f"steps[{len(steps)-1}]",
                target="output_contract",
                description="Last step has no output defined",
                severity="warning"
            )

        # Check output format alignment
        contract_format = output_contract.get("format")
        if contract_format and last_step.get("action"):
            action = last_step["action"].lower()
            format_keywords = {
                "json": ["json", "serialize", "dict"],
                "text": ["text", "string", "format"],
                "markdown": ["markdown", "md", "document"],
            }
            if contract_format in format_keywords:
                if not any(kw in action for kw in format_keywords[contract_format]):
                    result.add_issue(
                        category="FORMAT_MISMATCH",
                        source=f"steps[{len(steps)-1}].action",
                        target=f"output_contract.format ({contract_format})",
                        description=f"Step action '{action}' may not produce {contract_format} format",
                        severity="warning"
                    )

    def _check_failure_modes_edge_cases(
        self,
        failure_modes: List[Dict[str, Any]],
        edge_cases: List[Dict[str, Any]],
        result: ConsistencyValidationResult
    ) -> None:
        """Check alignment between failure modes and edge cases."""
        # Get all error codes from failure modes
        failure_codes = {fm.get("code") for fm in failure_modes if fm.get("code")}

        # Get all error codes referenced in edge cases
        edge_case_codes = set()
        for ec in edge_cases:
            expected = ec.get("expected", {})
            if isinstance(expected, dict):
                if expected.get("code"):
                    edge_case_codes.add(expected["code"])
                if expected.get("status") == "error" and expected.get("error_code"):
                    edge_case_codes.add(expected["error_code"])

            if ec.get("covers_failure"):
                edge_case_codes.add(ec["covers_failure"])

        # Check for codes in edge cases not defined in failure modes
        undefined_codes = edge_case_codes - failure_codes
        for code in undefined_codes:
            result.add_issue(
                category="UNDEFINED_FAILURE_CODE",
                source="edge_cases",
                target=f"failure_modes.{code}",
                description=f"Error code '{code}' used in edge cases but not defined in failure_modes",
                severity="error"
            )

        # Check for retryable consistency
        for ec in edge_cases:
            expected = ec.get("expected", {})
            if isinstance(expected, dict) and expected.get("retryable") is not None:
                code = expected.get("code") or ec.get("covers_failure")
                if code:
                    fm = next((f for f in failure_modes if f.get("code") == code), None)
                    if fm and fm.get("retryable") != expected.get("retryable"):
                        result.add_issue(
                            category="RETRYABLE_MISMATCH",
                            source=f"edge_cases.{ec.get('case')}",
                            target=f"failure_modes.{code}",
                            description=f"Retryable flag mismatch for '{code}'",
                            severity="warning"
                        )

    def _check_decision_rule_references(
        self,
        decision_rules: Any,
        failure_modes: List[Dict[str, Any]],
        result: ConsistencyValidationResult
    ) -> None:
        """Check that decision rules reference valid failure codes."""
        failure_codes = {fm.get("code") for fm in failure_modes if fm.get("code")}

        rules = self._extract_rules(decision_rules)

        for rule in rules:
            rule_id = rule.get("id", "unknown")
            then = rule.get("then", {})

            if isinstance(then, dict):
                code = then.get("code")
                if code and code not in failure_codes:
                    result.add_issue(
                        category="UNDEFINED_RULE_CODE",
                        source=f"decision_rules.{rule_id}.then.code",
                        target=f"failure_modes.{code}",
                        description=f"Code '{code}' not defined in failure_modes",
                        severity="warning"
                    )

    def _check_orphan_definitions(
        self,
        spec_data: Dict[str, Any],
        result: ConsistencyValidationResult
    ) -> None:
        """Check for orphan definitions that are never referenced."""
        # Get all step outputs
        step_outputs = {
            s.get("output")
            for s in spec_data.get("steps", [])
            if s.get("output")
        }

        # Get all based_on references
        based_on_refs = set()
        for step in spec_data.get("steps", []):
            for ref in step.get("based_on", []):
                based_on_refs.add(ref)

        # Find orphan outputs (defined but never used)
        orphan_outputs = step_outputs - based_on_refs
        for output in orphan_outputs:
            # Last output is expected to be "orphan" (it's the final result)
            steps = spec_data.get("steps", [])
            if steps and steps[-1].get("output") == output:
                continue
            result.add_orphan(f"step output: {output}")

        # Check for orphan failure modes (not referenced anywhere)
        failure_codes = {
            fm.get("code")
            for fm in spec_data.get("failure_modes", [])
            if fm.get("code")
        }

        # Collect all code references
        referenced_codes = set()

        # From decision rules
        decision_rules = spec_data.get("decision_rules", {})
        for rule in self._extract_rules(decision_rules):
            then = rule.get("then", {})
            if isinstance(then, dict) and then.get("code"):
                referenced_codes.add(then["code"])

        # From edge cases
        for ec in spec_data.get("edge_cases", []):
            expected = ec.get("expected", {})
            if isinstance(expected, dict) and expected.get("code"):
                referenced_codes.add(expected["code"])
            if ec.get("covers_failure"):
                referenced_codes.add(ec["covers_failure"])

        orphan_codes = failure_codes - referenced_codes
        for code in orphan_codes:
            result.add_orphan(f"failure_mode: {code}")
            result.add_issue(
                category="ORPHAN_FAILURE_MODE",
                source=f"failure_modes.{code}",
                target="(unused)",
                description=f"Failure mode '{code}' is defined but never referenced",
                severity="warning"
            )

    def _check_context_references(
        self,
        context: Dict[str, Any],
        result: ConsistencyValidationResult
    ) -> None:
        """Check that context.works_with references valid skills."""
        if not context or not self.known_skills:
            return

        works_with = context.get("works_with", [])
        for ref in works_with:
            skill_name = ref.get("skill")
            if skill_name and skill_name not in self.known_skills:
                result.add_issue(
                    category="UNKNOWN_SKILL_REFERENCE",
                    source="context.works_with",
                    target=skill_name,
                    description=f"Referenced skill '{skill_name}' is not known",
                    severity="warning"
                )
