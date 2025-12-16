"""
Logic Analyzer.

Analyzes decision rules for coverage, conflicts, and dead branches.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

from .parser import SimpleExpressionParser
from .evaluator import JsonLogicEvaluator


@dataclass
class Branch:
    """Represents a decision branch."""
    rule_id: str
    condition: str
    action: Dict[str, Any]
    priority: int = 0
    is_default: bool = False
    reachable: bool = True
    covered_by_tests: bool = False


@dataclass
class ConflictResult:
    """Result of conflict detection."""
    has_conflict: bool
    conflicting_rules: List[Tuple[str, str]] = field(default_factory=list)
    resolution: str = ""
    warnings: List[str] = field(default_factory=list)


@dataclass
class AnalysisResult:
    """Result of decision rules analysis."""
    total_branches: int = 0
    reachable_branches: int = 0
    dead_branches: List[str] = field(default_factory=list)
    uncovered_combinations: List[Dict[str, Any]] = field(default_factory=list)
    conflict_result: Optional[ConflictResult] = None
    branch_details: List[Branch] = field(default_factory=list)
    coverage_gaps: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "total_branches": self.total_branches,
            "reachable_branches": self.reachable_branches,
            "dead_branches": self.dead_branches,
            "uncovered_combinations": self.uncovered_combinations,
            "conflict_result": {
                "has_conflict": self.conflict_result.has_conflict,
                "conflicting_rules": self.conflict_result.conflicting_rules,
                "resolution": self.conflict_result.resolution,
                "warnings": self.conflict_result.warnings,
            } if self.conflict_result else None,
            "coverage_gaps": self.coverage_gaps,
        }


class LogicAnalyzer:
    """
    Analyzes decision rules for completeness and correctness.

    Provides:
    - Branch enumeration from decision_rules
    - Dead branch detection
    - Uncovered input combination finder
    - Conflict detection and resolution
    """

    def __init__(self):
        """Initialize the analyzer."""
        self.parser = SimpleExpressionParser()
        self.evaluator = JsonLogicEvaluator()

    def analyze(
        self,
        spec_data: Dict[str, Any],
        test_inputs: Optional[List[Dict[str, Any]]] = None
    ) -> AnalysisResult:
        """
        Analyze decision rules.

        Args:
            spec_data: The specification data.
            test_inputs: Optional test inputs to check coverage.

        Returns:
            AnalysisResult with analysis details.
        """
        result = AnalysisResult()

        decision_rules = spec_data.get("decision_rules", {})
        inputs = spec_data.get("inputs", [])

        # Extract rules configuration
        config = {}
        if isinstance(decision_rules, dict):
            config = decision_rules.get("_config", {})

        # Enumerate branches
        branches = self._enumerate_branches(decision_rules)
        result.total_branches = len(branches)
        result.branch_details = branches

        # Detect dead branches
        dead = self._detect_dead_branches(branches, config)
        result.dead_branches = dead
        result.reachable_branches = len(branches) - len(dead)

        # Check for conflicts
        result.conflict_result = self._detect_conflicts(branches, config)

        # Find uncovered combinations
        if test_inputs:
            uncovered = self._find_uncovered_combinations(
                branches, inputs, test_inputs
            )
            result.uncovered_combinations = uncovered

        # Generate coverage gaps
        result.coverage_gaps = self._generate_coverage_gaps(
            branches, inputs, test_inputs
        )

        return result

    def _enumerate_branches(
        self,
        decision_rules: Any
    ) -> List[Branch]:
        """Enumerate all branches from decision rules."""
        branches = []

        rules = []
        if isinstance(decision_rules, list):
            rules = decision_rules
        elif isinstance(decision_rules, dict):
            rules = [
                v for k, v in decision_rules.items()
                if k != "_config" and isinstance(v, dict)
            ]

        for i, rule in enumerate(rules):
            rule_id = rule.get("id", f"rule_{i}")
            when = rule.get("when", True)
            then = rule.get("then", {})
            priority = rule.get("priority", 0)
            is_default = rule.get("is_default", False)

            # Convert when to string if needed
            condition = str(when) if when is not True else "true"

            branches.append(Branch(
                rule_id=rule_id,
                condition=condition,
                action=then if isinstance(then, dict) else {"value": then},
                priority=priority,
                is_default=is_default,
            ))

        return branches

    def _detect_dead_branches(
        self,
        branches: List[Branch],
        config: Dict[str, Any]
    ) -> List[str]:
        """
        Detect branches that can never be reached.

        A branch is dead if:
        - Its condition is always false
        - A higher priority branch always matches first
        - A previous branch with same condition exists (first_match)
        """
        dead = []
        match_strategy = config.get("match_strategy", "first_match")

        # Track conditions we've seen
        seen_conditions: Set[str] = set()

        for branch in branches:
            # Check for duplicate conditions in first_match mode
            if match_strategy == "first_match":
                if branch.condition in seen_conditions and not branch.is_default:
                    dead.append(branch.rule_id)
                    branch.reachable = False
                    continue

            # Check for always-false conditions
            if self._is_always_false(branch.condition):
                dead.append(branch.rule_id)
                branch.reachable = False
                continue

            # Check if higher priority rules shadow this one
            if match_strategy == "priority":
                for other in branches:
                    if other.rule_id == branch.rule_id:
                        continue
                    if other.priority > branch.priority:
                        if self._conditions_overlap(other.condition, branch.condition):
                            # This rule might be shadowed
                            pass  # Could add warning here

            seen_conditions.add(branch.condition)

        return dead

    def _is_always_false(self, condition: str) -> bool:
        """Check if a condition is always false."""
        # Simple checks
        if condition.lower() in ("false", "0", "none", "null"):
            return True

        # Check for contradictions like "x == 1 and x == 2"
        if " and " in condition.lower():
            # Very basic contradiction detection
            parts = condition.lower().split(" and ")
            for i, p1 in enumerate(parts):
                for p2 in parts[i+1:]:
                    if "==" in p1 and "==" in p2:
                        var1 = p1.split("==")[0].strip()
                        var2 = p2.split("==")[0].strip()
                        if var1 == var2:
                            val1 = p1.split("==")[1].strip()
                            val2 = p2.split("==")[1].strip()
                            if val1 != val2:
                                return True

        return False

    def _conditions_overlap(self, cond1: str, cond2: str) -> bool:
        """Check if two conditions can both be true for same input."""
        # Simplified overlap detection
        if cond1 == "true" or cond2 == "true":
            return True

        # Same condition overlaps with itself
        if cond1 == cond2:
            return True

        # For more complex overlap detection, would need symbolic analysis
        return False

    def _detect_conflicts(
        self,
        branches: List[Branch],
        config: Dict[str, Any]
    ) -> ConflictResult:
        """Detect conflicts between rules."""
        result = ConflictResult(has_conflict=False)
        match_strategy = config.get("match_strategy", "first_match")
        conflict_resolution = config.get("conflict_resolution", "first_wins")

        # Find rules with same condition but different actions
        condition_map: Dict[str, List[Branch]] = {}
        for branch in branches:
            if branch.condition not in condition_map:
                condition_map[branch.condition] = []
            condition_map[branch.condition].append(branch)

        for condition, matching_branches in condition_map.items():
            if len(matching_branches) > 1:
                # Check if actions are different
                actions = [str(b.action) for b in matching_branches]
                if len(set(actions)) > 1:
                    result.has_conflict = True
                    for i, b1 in enumerate(matching_branches):
                        for b2 in matching_branches[i+1:]:
                            result.conflicting_rules.append((b1.rule_id, b2.rule_id))

        # Apply resolution strategy
        if result.has_conflict:
            if conflict_resolution == "error":
                result.resolution = "error"
                result.warnings.append(
                    "Conflicting rules detected. Resolution strategy is 'error'."
                )
            elif conflict_resolution == "warn":
                result.resolution = "first_wins"
                result.warnings.append(
                    "Conflicting rules detected. Using first matching rule."
                )
            else:  # first_wins
                result.resolution = "first_wins"

        return result

    def _find_uncovered_combinations(
        self,
        branches: List[Branch],
        inputs: List[Dict[str, Any]],
        test_inputs: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Find input combinations not covered by tests."""
        uncovered = []

        # Generate representative combinations from input domains
        combinations = self._generate_test_combinations(inputs, max_count=50)

        # Check which combinations trigger each branch
        for combo in combinations:
            combo_covered = False
            for test in test_inputs:
                if self._inputs_match(combo, test):
                    combo_covered = True
                    break

            if not combo_covered:
                # Check which branch this combo would trigger
                triggered_branch = self._find_triggered_branch(branches, combo)
                if triggered_branch:
                    uncovered.append({
                        "input": combo,
                        "triggers_rule": triggered_branch.rule_id
                    })

        return uncovered[:20]  # Limit results

    def _generate_test_combinations(
        self,
        inputs: List[Dict[str, Any]],
        max_count: int = 50
    ) -> List[Dict[str, Any]]:
        """Generate test combinations from input domains."""
        combinations = []

        # Build value sets for each input
        input_values: Dict[str, List[Any]] = {}

        for inp in inputs:
            name = inp.get("name")
            domain = inp.get("domain", {})
            domain_type = domain.get("type", "any")

            if domain_type == "enum":
                input_values[name] = list(domain.get("values", ["test"]))
            elif domain_type == "boolean":
                input_values[name] = [True, False]
            elif domain_type == "range":
                min_val = domain.get("min", 0)
                max_val = domain.get("max", 10)
                input_values[name] = [min_val, max_val]
            else:
                input_values[name] = ["test_value"]

        if not input_values:
            return []

        # Simple cartesian product with limit
        input_names = list(input_values.keys())

        def generate(index: int, current: Dict[str, Any]) -> None:
            if len(combinations) >= max_count:
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

    def _inputs_match(
        self,
        combo: Dict[str, Any],
        test: Dict[str, Any]
    ) -> bool:
        """Check if test input matches combination."""
        for key, val in combo.items():
            if key in test and test[key] == val:
                continue
            return False
        return True

    def _find_triggered_branch(
        self,
        branches: List[Branch],
        inputs: Dict[str, Any]
    ) -> Optional[Branch]:
        """Find which branch would be triggered by inputs."""
        for branch in branches:
            if branch.is_default:
                continue

            # Try to evaluate condition
            try:
                # Parse condition
                json_logic = self.parser.parse(branch.condition)
                if json_logic:
                    result = self.evaluator.evaluate(json_logic, inputs)
                    if result:
                        return branch
            except Exception:
                pass

        # Return default branch if exists
        for branch in branches:
            if branch.is_default:
                return branch

        return None

    def _generate_coverage_gaps(
        self,
        branches: List[Branch],
        inputs: List[Dict[str, Any]],
        test_inputs: Optional[List[Dict[str, Any]]]
    ) -> List[str]:
        """Generate list of coverage gaps."""
        gaps = []

        # Check for untested branches
        tested_rules: Set[str] = set()
        if test_inputs:
            for test in test_inputs:
                triggered = self._find_triggered_branch(branches, test)
                if triggered:
                    tested_rules.add(triggered.rule_id)

        for branch in branches:
            if branch.reachable and branch.rule_id not in tested_rules:
                gaps.append(f"Rule '{branch.rule_id}' has no test coverage")

        # Check for missing edge cases
        if not any(b.is_default for b in branches):
            gaps.append("No default rule defined - edge cases may not be handled")

        return gaps


def resolve_conflict(
    rule1: Dict[str, Any],
    rule2: Dict[str, Any],
    strategy: str = "first_wins"
) -> Tuple[Dict[str, Any], List[str]]:
    """
    Resolve conflict between two rules.

    Args:
        rule1: First rule.
        rule2: Second rule.
        strategy: Resolution strategy (first_wins, warn, error).

    Returns:
        Tuple of (winning_rule, warnings).
    """
    warnings = []

    if strategy == "error":
        raise ValueError(
            f"Conflicting rules: {rule1.get('id')} and {rule2.get('id')}"
        )

    if strategy == "warn":
        warnings.append(
            f"Conflict between {rule1.get('id')} and {rule2.get('id')}. "
            f"Using {rule1.get('id')}."
        )

    # Use priority if available
    p1 = rule1.get("priority", 0)
    p2 = rule2.get("priority", 0)

    if p1 >= p2:
        return rule1, warnings
    else:
        return rule2, warnings
