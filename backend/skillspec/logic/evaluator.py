"""
Expression Evaluator for decision rules.

Evaluates JSON Logic expressions against input data.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Union


class ExpressionEvaluator:
    """
    Evaluator for JSON Logic expressions.

    Supports standard JSON Logic operators plus custom extensions:
    - len: Get length of string/array
    - matches: Regex matching
    """

    def evaluate(
        self,
        logic: Union[Dict, bool, Any],
        data: Dict[str, Any]
    ) -> Any:
        """
        Evaluate a JSON Logic expression against data.

        Args:
            logic: The JSON Logic expression.
            data: The data context.

        Returns:
            The evaluation result.
        """
        # Handle primitives
        if isinstance(logic, bool):
            return logic
        if not isinstance(logic, dict):
            return logic

        # Get the operator and arguments
        if len(logic) != 1:
            return logic

        operator = list(logic.keys())[0]
        args = logic[operator]

        # Handle operators
        if operator == "var":
            return self._get_var(args, data)

        if operator == "and":
            return self._eval_and(args, data)

        if operator == "or":
            return self._eval_or(args, data)

        if operator == "!":
            return not self._to_bool(self.evaluate(args, data))

        if operator == "==":
            return self._eval_comparison(args, data, lambda a, b: a == b)

        if operator == "!=":
            return self._eval_comparison(args, data, lambda a, b: a != b)

        if operator == "<":
            return self._eval_comparison(args, data, lambda a, b: a < b)

        if operator == ">":
            return self._eval_comparison(args, data, lambda a, b: a > b)

        if operator == "<=":
            return self._eval_comparison(args, data, lambda a, b: a <= b)

        if operator == ">=":
            return self._eval_comparison(args, data, lambda a, b: a >= b)

        if operator == "in":
            return self._eval_in(args, data)

        if operator == "len":
            return self._eval_len(args, data)

        if operator == "matches":
            return self._eval_matches(args, data)

        if operator == "if":
            return self._eval_if(args, data)

        # Unknown operator, return as-is
        return logic

    def _get_var(self, path: Union[str, List], data: Dict[str, Any]) -> Any:
        """Get a variable from data using dot notation."""
        if isinstance(path, list):
            path = path[0] if path else ""
            default = path[1] if len(path) > 1 else None
        else:
            default = None

        if not path:
            return data

        # Handle special _len_ prefix
        if path.startswith("_len_"):
            actual_path = path[5:]
            value = self._get_var(actual_path, data)
            return len(value) if value is not None else 0

        # Navigate the path
        parts = path.split(".")
        current = data

        for part in parts:
            if isinstance(current, dict):
                current = current.get(part)
            elif isinstance(current, list):
                try:
                    idx = int(part)
                    current = current[idx]
                except (ValueError, IndexError):
                    return default
            else:
                return default

            if current is None:
                return default

        return current

    def _eval_and(self, args: List, data: Dict) -> bool:
        """Evaluate AND expression."""
        if not isinstance(args, list):
            return self._to_bool(self.evaluate(args, data))

        for arg in args:
            if not self._to_bool(self.evaluate(arg, data)):
                return False
        return True

    def _eval_or(self, args: List, data: Dict) -> bool:
        """Evaluate OR expression."""
        if not isinstance(args, list):
            return self._to_bool(self.evaluate(args, data))

        for arg in args:
            if self._to_bool(self.evaluate(arg, data)):
                return True
        return False

    def _eval_comparison(self, args: List, data: Dict, op) -> bool:
        """Evaluate a comparison."""
        if not isinstance(args, list) or len(args) != 2:
            return False

        left = self.evaluate(args[0], data)
        right = self.evaluate(args[1], data)

        try:
            return op(left, right)
        except TypeError:
            # Type mismatch, try string comparison
            return op(str(left), str(right))

    def _eval_in(self, args: List, data: Dict) -> bool:
        """Evaluate 'in' (contains) expression."""
        if not isinstance(args, list) or len(args) != 2:
            return False

        needle = self.evaluate(args[0], data)
        haystack = self.evaluate(args[1], data)

        if isinstance(haystack, str):
            return str(needle) in haystack
        if isinstance(haystack, (list, tuple)):
            return needle in haystack
        if isinstance(haystack, dict):
            return needle in haystack

        return False

    def _eval_len(self, arg: Any, data: Dict) -> int:
        """Evaluate len expression."""
        value = self.evaluate(arg, data)
        if value is None:
            return 0
        try:
            return len(value)
        except TypeError:
            return 0

    def _eval_matches(self, args: List, data: Dict) -> bool:
        """Evaluate regex match expression."""
        if not isinstance(args, list) or len(args) != 2:
            return False

        string = self.evaluate(args[0], data)
        pattern = self.evaluate(args[1], data)

        if not isinstance(string, str) or not isinstance(pattern, str):
            return False

        try:
            return bool(re.search(pattern, string))
        except re.error:
            return False

    def _eval_if(self, args: List, data: Dict) -> Any:
        """Evaluate if-then-else expression."""
        if not isinstance(args, list):
            return None

        # Process condition-value pairs
        i = 0
        while i < len(args) - 1:
            condition = self.evaluate(args[i], data)
            if self._to_bool(condition):
                return self.evaluate(args[i + 1], data)
            i += 2

        # Return else value if present
        if i < len(args):
            return self.evaluate(args[i], data)

        return None

    def _to_bool(self, value: Any) -> bool:
        """Convert value to boolean (JSON Logic truthy rules)."""
        if value is None:
            return False
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)):
            return value != 0
        if isinstance(value, str):
            return len(value) > 0
        if isinstance(value, (list, dict)):
            return len(value) > 0
        return bool(value)

    def evaluate_rule(
        self,
        rule: Dict[str, Any],
        data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Evaluate a decision rule against data.

        Args:
            rule: The decision rule with 'when' and 'then'.
            data: The input data.

        Returns:
            The 'then' value if condition matches, None otherwise.
        """
        when = rule.get("when")
        then = rule.get("then")

        if when is None:
            return None

        # Evaluate the condition
        from .parser import ExpressionParser
        parser = ExpressionParser()

        if isinstance(when, str):
            logic = parser.parse(when)
        else:
            logic = when

        result = self.evaluate(logic, data)

        if self._to_bool(result):
            return then

        return None

    def evaluate_rules(
        self,
        rules: List[Dict[str, Any]],
        data: Dict[str, Any],
        match_strategy: str = "first_match",
        conflict_resolution: str = "first_wins"
    ) -> List[Dict[str, Any]]:
        """
        Evaluate multiple rules against data.

        Args:
            rules: List of decision rules.
            data: The input data.
            match_strategy: How to handle matches (first_match, priority, all_match).
            conflict_resolution: How to handle conflicts (first_wins, warn, error).

        Returns:
            List of matching rule outcomes.

        Raises:
            ValueError: If conflict_resolution is 'error' and conflicts exist.
        """
        matches = []
        warnings = []

        # Sort by priority if using priority strategy
        if match_strategy == "priority":
            rules = sorted(rules, key=lambda r: r.get("priority", 0), reverse=True)

        for rule in rules:
            result = self.evaluate_rule(rule, data)
            if result is not None:
                matches.append({
                    "rule_id": rule.get("id"),
                    "result": result,
                })

                if match_strategy == "first_match":
                    break

        # Handle conflicts for all_match strategy
        if match_strategy == "all_match" and len(matches) > 1:
            # Check for conflicting results
            unique_results = set(str(m["result"]) for m in matches)
            if len(unique_results) > 1:
                if conflict_resolution == "error":
                    rule_ids = [m["rule_id"] for m in matches]
                    raise ValueError(
                        f"Conflicting rules matched: {rule_ids}. "
                        "Use conflict_resolution='first_wins' or 'warn' to resolve."
                    )
                elif conflict_resolution == "warn":
                    rule_ids = [m["rule_id"] for m in matches]
                    warnings.append(
                        f"Conflicting rules matched: {rule_ids}. "
                        f"Using first match: {matches[0]['rule_id']}"
                    )
                # For first_wins, silently use first match

        # Attach warnings to first match if any
        if matches and warnings:
            matches[0]["warnings"] = warnings

        return matches


class JsonLogicEvaluator(ExpressionEvaluator):
    """Alias for ExpressionEvaluator for compatibility."""
    pass


class RuleEngine:
    """
    High-level rule engine for evaluating decision rules.

    Provides convenient methods for rule evaluation with configuration.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the rule engine.

        Args:
            config: Configuration with match_strategy and conflict_resolution.
        """
        self.evaluator = ExpressionEvaluator()
        self.config = config or {}
        self.match_strategy = self.config.get("match_strategy", "first_match")
        self.conflict_resolution = self.config.get("conflict_resolution", "first_wins")

    def evaluate(
        self,
        rules: List[Dict[str, Any]],
        data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Evaluate rules against data.

        Args:
            rules: List of decision rules.
            data: Input data.

        Returns:
            Evaluation result with matches and any warnings.
        """
        try:
            matches = self.evaluator.evaluate_rules(
                rules, data,
                match_strategy=self.match_strategy,
                conflict_resolution=self.conflict_resolution
            )

            return {
                "success": True,
                "matches": matches,
                "matched_count": len(matches),
                "first_match": matches[0] if matches else None,
                "warnings": matches[0].get("warnings", []) if matches else [],
            }

        except ValueError as e:
            return {
                "success": False,
                "error": str(e),
                "matches": [],
                "matched_count": 0,
            }

    def find_applicable_rule(
        self,
        rules: List[Dict[str, Any]],
        data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Find the first applicable rule.

        Args:
            rules: List of decision rules.
            data: Input data.

        Returns:
            The matched rule or None.
        """
        result = self.evaluate(rules, data)
        if result["success"] and result["first_match"]:
            return result["first_match"]["result"]
        return None
