"""
Coverage Validation (Layer 3).

Validates coverage aspects of a skill specification:
- Structural coverage: edge_case <-> failure_modes mapping
- Behavioral coverage: tests -> decision_rules coverage
- Domain-based coverage calculation
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple


@dataclass
class CoverageGap:
    """Represents a coverage gap in the specification."""

    gap_type: str  # structural | behavioral
    category: str
    item: str
    description: str
    severity: str = "warning"

    def __str__(self) -> str:
        return f"[{self.gap_type.upper()}] {self.category}: {self.item} - {self.description}"


@dataclass
class CoverageMetrics:
    """Coverage metrics for a specification."""

    # Structural coverage
    failure_modes_covered: int = 0
    failure_modes_total: int = 0
    decision_rules_referenced: int = 0
    decision_rules_total: int = 0
    inputs_referenced: int = 0
    inputs_total: int = 0

    # Behavioral coverage (from tests/examples)
    edge_cases_with_input: int = 0
    edge_cases_total: int = 0
    rules_tested: int = 0
    errors_tested: int = 0

    @property
    def structural_score(self) -> float:
        """Calculate structural coverage score (0-100)."""
        scores = []

        if self.failure_modes_total > 0:
            scores.append(self.failure_modes_covered / self.failure_modes_total)

        if self.decision_rules_total > 0:
            scores.append(self.decision_rules_referenced / self.decision_rules_total)

        if self.inputs_total > 0:
            scores.append(self.inputs_referenced / self.inputs_total)

        if not scores:
            return 100.0

        return round(sum(scores) / len(scores) * 100, 1)

    @property
    def behavioral_score(self) -> float:
        """Calculate behavioral coverage score (0-100)."""
        if self.edge_cases_total == 0:
            return 0.0

        return round(self.edge_cases_with_input / self.edge_cases_total * 100, 1)


@dataclass
class CoverageValidationResult:
    """Result of coverage validation."""

    valid: bool
    gaps: List[CoverageGap] = field(default_factory=list)
    metrics: CoverageMetrics = field(default_factory=CoverageMetrics)

    def add_gap(
        self,
        gap_type: str,
        category: str,
        item: str,
        description: str,
        severity: str = "warning"
    ) -> None:
        """Add a coverage gap."""
        self.gaps.append(CoverageGap(
            gap_type=gap_type,
            category=category,
            item=item,
            description=description,
            severity=severity
        ))
        if severity == "error":
            self.valid = False


class CoverageValidator:
    """
    Validates coverage aspects of skill specifications (Layer 3).

    Checks:
    - Structural: edge_cases <-> failure_modes mapping
    - Structural: inputs <-> decision_rules references
    - Structural: default path existence
    - Behavioral: rule_id coverage from tests
    """

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

    def validate(self, spec_data: Dict[str, Any]) -> CoverageValidationResult:
        """
        Validate spec coverage.

        Args:
            spec_data: The specification data as a dictionary.

        Returns:
            CoverageValidationResult with validation status and gaps.
        """
        result = CoverageValidationResult(valid=True)

        # Extract components
        inputs = spec_data.get("inputs", [])
        decision_rules = spec_data.get("decision_rules", {})
        failure_modes = spec_data.get("failure_modes", [])
        edge_cases = spec_data.get("edge_cases", [])
        steps = spec_data.get("steps", [])

        # Structural coverage checks
        self._check_failure_modes_coverage(failure_modes, edge_cases, result)
        self._check_decision_rules_coverage(decision_rules, edge_cases, result)
        self._check_inputs_coverage(inputs, decision_rules, result)
        self._check_default_path(decision_rules, result)
        self._check_steps_chain(steps, result)

        # Behavioral coverage checks
        self._check_edge_case_completeness(edge_cases, result)

        return result

    def _check_failure_modes_coverage(
        self,
        failure_modes: List[Dict[str, Any]],
        edge_cases: List[Dict[str, Any]],
        result: CoverageValidationResult
    ) -> None:
        """Check that all failure modes are covered by edge cases."""
        failure_codes = {fm.get("code") for fm in failure_modes}
        result.metrics.failure_modes_total = len(failure_codes)

        # Find which failure modes are covered by edge cases
        covered_codes = set()
        for ec in edge_cases:
            # Check covers_failure field
            if ec.get("covers_failure"):
                covered_codes.add(ec["covers_failure"])

            # Check expected.code field
            expected = ec.get("expected", {})
            if isinstance(expected, dict) and expected.get("code"):
                covered_codes.add(expected["code"])

        result.metrics.failure_modes_covered = len(covered_codes & failure_codes)

        # Report uncovered failure modes
        uncovered = failure_codes - covered_codes
        for code in uncovered:
            result.add_gap(
                gap_type="structural",
                category="UNCOVERED_FAILURE_MODE",
                item=code,
                description=f"Failure mode '{code}' has no corresponding edge case"
            )

    def _check_decision_rules_coverage(
        self,
        decision_rules: Any,
        edge_cases: List[Dict[str, Any]],
        result: CoverageValidationResult
    ) -> None:
        """Check that decision rules are referenced by edge cases."""
        # Extract rules using helper function
        rules = self._extract_rules(decision_rules)
        rule_ids = {r.get("id") for r in rules if r.get("id")}

        result.metrics.decision_rules_total = len(rule_ids)

        # Find which rules are covered by edge cases
        covered_rules = set()
        for ec in edge_cases:
            if ec.get("covers_rule"):
                covered_rules.add(ec["covers_rule"])

        result.metrics.decision_rules_referenced = len(covered_rules & rule_ids)

        # Check for default rule
        has_default = any(r.get("is_default") for r in rules)

        # Report rules without edge case coverage (warning only)
        uncovered = rule_ids - covered_rules
        for rule_id in uncovered:
            result.add_gap(
                gap_type="structural",
                category="UNCOVERED_RULE",
                item=rule_id,
                description=f"Rule '{rule_id}' has no edge case with covers_rule reference",
                severity="warning"
            )

    def _check_inputs_coverage(
        self,
        inputs: List[Dict[str, Any]],
        decision_rules: Any,
        result: CoverageValidationResult
    ) -> None:
        """Check that inputs are referenced in decision rules."""
        input_names = {inp.get("name") for inp in inputs if inp.get("name")}
        result.metrics.inputs_total = len(input_names)

        # Extract input references from decision rules
        referenced_inputs = set()

        def extract_references(obj: Any) -> None:
            if isinstance(obj, str):
                for name in input_names:
                    if name in obj:
                        referenced_inputs.add(name)
            elif isinstance(obj, dict):
                for value in obj.values():
                    extract_references(value)
            elif isinstance(obj, list):
                for item in obj:
                    extract_references(item)

        extract_references(decision_rules)

        result.metrics.inputs_referenced = len(referenced_inputs & input_names)

        # Report unreferenced inputs (info only)
        unreferenced = input_names - referenced_inputs
        for name in unreferenced:
            result.add_gap(
                gap_type="structural",
                category="UNREFERENCED_INPUT",
                item=name,
                description=f"Input '{name}' is not referenced in any decision rule",
                severity="warning"
            )

    def _check_default_path(
        self,
        decision_rules: Any,
        result: CoverageValidationResult
    ) -> None:
        """Check that a default/fallback path exists."""
        rules = self._extract_rules(decision_rules)
        has_default = any(
            r.get("is_default") or r.get("when") is True
            for r in rules
        )

        if not has_default:
            result.add_gap(
                gap_type="structural",
                category="NO_DEFAULT_PATH",
                item="decision_rules",
                description="No default path defined (add is_default: true to a rule)",
                severity="warning"
            )

    def _check_steps_chain(
        self,
        steps: List[Dict[str, Any]],
        result: CoverageValidationResult
    ) -> None:
        """Check that step outputs form a complete chain."""
        outputs = set()
        for i, step in enumerate(steps):
            # Check based_on references
            based_on = step.get("based_on", [])
            for dep in based_on:
                if dep not in outputs:
                    result.add_gap(
                        gap_type="structural",
                        category="BROKEN_STEP_CHAIN",
                        item=f"steps[{i}].based_on",
                        description=f"Step '{step.get('id')}' depends on '{dep}' "
                                    f"which is not available",
                        severity="error"
                    )

            # Add output to available set
            if step.get("output"):
                outputs.add(step["output"])

    def _check_edge_case_completeness(
        self,
        edge_cases: List[Dict[str, Any]],
        result: CoverageValidationResult
    ) -> None:
        """Check edge case completeness."""
        result.metrics.edge_cases_total = len(edge_cases)

        # Count edge cases with input examples
        with_input = sum(1 for ec in edge_cases if ec.get("input_example") is not None)
        result.metrics.edge_cases_with_input = with_input

        # Check for basic edge case categories
        case_names = {ec.get("case", "").lower() for ec in edge_cases}

        # Common edge cases that should be present
        recommended_cases = [
            ("empty", "empty input"),
            ("null", "null input"),
            ("boundary", "boundary conditions"),
        ]

        for keyword, description in recommended_cases:
            if not any(keyword in name for name in case_names):
                result.add_gap(
                    gap_type="behavioral",
                    category="MISSING_EDGE_CASE",
                    item=description,
                    description=f"Consider adding edge case for: {description}",
                    severity="warning"
                )

    def calculate_domain_coverage(
        self,
        spec_data: Dict[str, Any],
        examples: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, float]:
        """
        Calculate domain-based coverage from examples.

        Args:
            spec_data: The specification data.
            examples: Test examples with input values.

        Returns:
            Dictionary of input_name -> coverage percentage.
        """
        if not examples:
            return {}

        inputs = spec_data.get("inputs", [])
        coverage = {}

        for inp in inputs:
            name = inp.get("name")
            domain = inp.get("domain", {})
            domain_type = domain.get("type", "any")

            if domain_type == "enum":
                # Calculate enum coverage
                values = set(domain.get("values", []))
                tested = set()
                for ex in examples:
                    input_val = ex.get("input", {}).get(name)
                    if input_val in values:
                        tested.add(input_val)
                coverage[name] = len(tested) / len(values) * 100 if values else 0

            elif domain_type == "boolean":
                # Check if both true and false are tested
                tested = set()
                for ex in examples:
                    input_val = ex.get("input", {}).get(name)
                    if isinstance(input_val, bool):
                        tested.add(input_val)
                coverage[name] = len(tested) / 2 * 100

            elif domain_type == "range":
                # Check boundary coverage (min, max, middle)
                min_val = domain.get("min", 0)
                max_val = domain.get("max", 100)
                boundaries = {min_val, max_val}
                tested = set()
                for ex in examples:
                    input_val = ex.get("input", {}).get(name)
                    if isinstance(input_val, (int, float)):
                        if input_val == min_val or input_val == max_val:
                            tested.add(input_val)
                coverage[name] = len(tested) / len(boundaries) * 100 if boundaries else 0

            else:
                # For 'any' type, just check if any example exists
                has_example = any(
                    name in ex.get("input", {})
                    for ex in examples
                )
                coverage[name] = 100 if has_example else 0

        return coverage

    def calculate_boundary_coverage(
        self,
        spec_data: Dict[str, Any],
        examples: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Dict[str, Any]]:
        """
        Calculate boundary input coverage from examples.

        Tracks whether boundary values (min, max, just-inside, just-outside)
        are tested for each input with a defined domain.

        Args:
            spec_data: The specification data.
            examples: Test examples with input values.

        Returns:
            Dictionary of input_name -> boundary coverage details.
        """
        if not examples:
            return {}

        inputs = spec_data.get("inputs", [])
        boundary_coverage = {}

        for inp in inputs:
            name = inp.get("name")
            domain = inp.get("domain", {})
            domain_type = domain.get("type", "any")

            boundaries = {
                "expected": [],
                "tested": [],
                "missing": [],
                "coverage_pct": 0.0
            }

            if domain_type == "range":
                min_val = domain.get("min")
                max_val = domain.get("max")

                # Define expected boundaries
                expected = []
                if min_val is not None:
                    expected.extend([
                        ("min", min_val),
                        ("below_min", min_val - 1),
                        ("above_min", min_val + 1),
                    ])
                if max_val is not None:
                    expected.extend([
                        ("max", max_val),
                        ("above_max", max_val + 1),
                        ("below_max", max_val - 1),
                    ])

                boundaries["expected"] = [e[0] for e in expected]

                # Check which boundaries are tested
                for ex in examples:
                    input_val = ex.get("input", {}).get(name)
                    if input_val is not None:
                        for bound_name, bound_val in expected:
                            if input_val == bound_val and bound_name not in boundaries["tested"]:
                                boundaries["tested"].append(bound_name)

                boundaries["missing"] = [
                    b for b in boundaries["expected"]
                    if b not in boundaries["tested"]
                ]

            elif domain_type == "enum":
                values = domain.get("values", [])
                boundaries["expected"] = values.copy()

                for ex in examples:
                    input_val = ex.get("input", {}).get(name)
                    if input_val in values and input_val not in boundaries["tested"]:
                        boundaries["tested"].append(input_val)

                boundaries["missing"] = [
                    v for v in boundaries["expected"]
                    if v not in boundaries["tested"]
                ]

            elif domain_type == "boolean":
                boundaries["expected"] = [True, False]
                for ex in examples:
                    input_val = ex.get("input", {}).get(name)
                    if isinstance(input_val, bool) and input_val not in boundaries["tested"]:
                        boundaries["tested"].append(input_val)

                boundaries["missing"] = [
                    v for v in boundaries["expected"]
                    if v not in boundaries["tested"]
                ]

            elif domain_type == "string" or (not domain_type or domain_type == "any"):
                # For strings/any, check empty, null, typical
                boundaries["expected"] = ["empty", "non_empty"]
                for ex in examples:
                    input_val = ex.get("input", {}).get(name)
                    if input_val == "" and "empty" not in boundaries["tested"]:
                        boundaries["tested"].append("empty")
                    elif input_val and "non_empty" not in boundaries["tested"]:
                        boundaries["tested"].append("non_empty")

                boundaries["missing"] = [
                    v for v in boundaries["expected"]
                    if v not in boundaries["tested"]
                ]

            # Calculate coverage percentage
            if boundaries["expected"]:
                boundaries["coverage_pct"] = round(
                    len(boundaries["tested"]) / len(boundaries["expected"]) * 100, 1
                )

            boundary_coverage[name] = boundaries

        return boundary_coverage

    def build_input_space_cartesian(
        self,
        spec_data: Dict[str, Any],
        max_combinations: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Build cartesian product of input domains.

        Creates all possible combinations of input values based on their
        defined domains, useful for generating comprehensive test cases.

        Args:
            spec_data: The specification data.
            max_combinations: Maximum combinations to generate (default 100).

        Returns:
            List of input combinations as dictionaries.
        """
        inputs = spec_data.get("inputs", [])

        # Build value sets for each input
        input_values: Dict[str, List[Any]] = {}

        for inp in inputs:
            name = inp.get("name")
            domain = inp.get("domain", {})
            domain_type = domain.get("type", "any")
            required = inp.get("required", False)

            values: List[Any] = []

            if domain_type == "enum":
                values = list(domain.get("values", []))
            elif domain_type == "boolean":
                values = [True, False]
            elif domain_type == "range":
                min_val = domain.get("min", 0)
                max_val = domain.get("max", 10)
                # Include boundaries and middle value
                mid = (min_val + max_val) // 2
                values = [min_val, mid, max_val]
                # Include out-of-range for error cases
                values.extend([min_val - 1, max_val + 1])
            else:
                # For any/string types, use representative values
                values = ["", "test_value", None]

            # Add None if not required
            if not required and None not in values:
                values.append(None)

            input_values[name] = values

        # Generate cartesian product
        if not input_values:
            return []

        # Use itertools-like product generation with limit
        combinations = []
        input_names = list(input_values.keys())

        def generate(index: int, current: Dict[str, Any]) -> None:
            if len(combinations) >= max_combinations:
                return

            if index == len(input_names):
                combinations.append(current.copy())
                return

            name = input_names[index]
            for val in input_values[name]:
                current[name] = val
                generate(index + 1, current)

        generate(0, {})

        return combinations

    def analyze_test_coverage(
        self,
        spec_data: Dict[str, Any],
        test_inputs: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Analyze coverage of provided test inputs against input space.

        Args:
            spec_data: The specification data.
            test_inputs: List of test input dictionaries.

        Returns:
            Coverage analysis report.
        """
        cartesian = self.build_input_space_cartesian(spec_data)
        boundary_cov = self.calculate_boundary_coverage(spec_data,
            [{"input": t} for t in test_inputs])

        # Calculate how many cartesian combinations are covered
        covered_combinations = 0
        for combo in cartesian:
            for test in test_inputs:
                if all(
                    test.get(k) == v or (v is None and k not in test)
                    for k, v in combo.items()
                    if v is not None
                ):
                    covered_combinations += 1
                    break

        return {
            "total_input_space": len(cartesian),
            "covered_combinations": covered_combinations,
            "combination_coverage_pct": round(
                covered_combinations / len(cartesian) * 100, 1
            ) if cartesian else 0,
            "boundary_coverage": boundary_cov,
            "uncovered_boundaries": {
                name: details["missing"]
                for name, details in boundary_cov.items()
                if details["missing"]
            },
            "recommendations": self._generate_coverage_recommendations(boundary_cov)
        }

    def _generate_coverage_recommendations(
        self,
        boundary_coverage: Dict[str, Dict[str, Any]]
    ) -> List[str]:
        """Generate recommendations for improving coverage."""
        recommendations = []

        for name, details in boundary_coverage.items():
            if details["missing"]:
                missing_str = ", ".join(str(m) for m in details["missing"][:3])
                recommendations.append(
                    f"Add test for '{name}' with values: {missing_str}"
                )

            if details["coverage_pct"] < 50:
                recommendations.append(
                    f"Input '{name}' has low coverage ({details['coverage_pct']}%). "
                    "Consider adding more test cases."
                )

        return recommendations
