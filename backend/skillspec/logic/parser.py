"""
Expression Parser for decision rules.

Parses simple syntax expressions into JSON Logic format.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple, Union


@dataclass
class ParseError:
    """Represents a parsing error."""
    message: str
    position: int
    expression: str


class ExpressionParser:
    """
    Parser for simple decision rule expressions.

    Converts expressions like:
        "len(input) == 0"
        "input.type == 'A' AND confidence < 0.7"

    Into JSON Logic format:
        {"==": [{"var": "len_input"}, 0]}
        {"and": [{"==": [{"var": "input.type"}, "A"]}, {"<": [{"var": "confidence"}, 0.7]}]}
    """

    # Supported operators (in order of precedence)
    BINARY_OPS = {
        "AND": "and",
        "OR": "or",
        "==": "==",
        "!=": "!=",
        "<=": "<=",
        ">=": ">=",
        "<": "<",
        ">": ">",
    }

    UNARY_OPS = {
        "NOT": "!",
    }

    # Supported functions
    FUNCTIONS = {
        "len": "len",
        "contains": "in",
        "matches": "matches",
        "is_empty": "is_empty",
        "is_null": "is_null",
    }

    def parse(self, expression: Union[str, bool, Dict]) -> Dict[str, Any]:
        """
        Parse an expression into JSON Logic.

        Args:
            expression: The expression to parse.

        Returns:
            JSON Logic representation.
        """
        if isinstance(expression, bool):
            return expression

        if isinstance(expression, dict):
            # Already JSON Logic, pass through
            return expression

        if not isinstance(expression, str):
            raise ValueError(f"Expected string expression, got {type(expression)}")

        expression = expression.strip()

        if not expression:
            raise ValueError("Empty expression")

        # Handle literal "true" / "false"
        if expression.lower() == "true":
            return True
        if expression.lower() == "false":
            return False

        return self._parse_expression(expression)

    def _parse_expression(self, expr: str) -> Dict[str, Any]:
        """Parse a full expression."""
        # Try to parse as OR expression (lowest precedence)
        return self._parse_or(expr)

    def _parse_or(self, expr: str) -> Dict[str, Any]:
        """Parse OR expressions."""
        parts = self._split_by_operator(expr, "OR")
        if len(parts) > 1:
            return {"or": [self._parse_and(p.strip()) for p in parts]}
        return self._parse_and(expr)

    def _parse_and(self, expr: str) -> Dict[str, Any]:
        """Parse AND expressions."""
        parts = self._split_by_operator(expr, "AND")
        if len(parts) > 1:
            return {"and": [self._parse_not(p.strip()) for p in parts]}
        return self._parse_not(expr)

    def _parse_not(self, expr: str) -> Dict[str, Any]:
        """Parse NOT expressions."""
        expr = expr.strip()
        if expr.upper().startswith("NOT "):
            inner = expr[4:].strip()
            return {"!": self._parse_comparison(inner)}
        return self._parse_comparison(expr)

    def _parse_comparison(self, expr: str) -> Dict[str, Any]:
        """Parse comparison expressions."""
        # Try each comparison operator
        for op in ["<=", ">=", "!=", "==", "<", ">"]:
            if op in expr:
                parts = expr.split(op, 1)
                if len(parts) == 2:
                    left = self._parse_value(parts[0].strip())
                    right = self._parse_value(parts[1].strip())
                    return {op: [left, right]}

        # No comparison operator found, parse as value
        return self._parse_value(expr)

    def _parse_value(self, expr: str) -> Any:
        """Parse a value (variable, literal, or function call)."""
        expr = expr.strip()

        # Handle parentheses
        if expr.startswith("(") and expr.endswith(")"):
            return self._parse_expression(expr[1:-1])

        # Handle string literals
        if (expr.startswith("'") and expr.endswith("'")) or \
           (expr.startswith('"') and expr.endswith('"')):
            return expr[1:-1]

        # Handle numeric literals
        try:
            if "." in expr:
                return float(expr)
            return int(expr)
        except ValueError:
            pass

        # Handle boolean literals
        if expr.lower() == "true":
            return True
        if expr.lower() == "false":
            return False

        # Handle function calls
        func_match = re.match(r"(\w+)\((.+)\)", expr)
        if func_match:
            func_name = func_match.group(1)
            args = func_match.group(2)
            return self._parse_function(func_name, args)

        # Handle variable reference
        return {"var": expr}

    def _parse_function(self, name: str, args: str) -> Dict[str, Any]:
        """Parse a function call."""
        if name not in self.FUNCTIONS:
            raise ValueError(f"Unknown function: {name}")

        json_logic_op = self.FUNCTIONS[name]

        # Parse arguments
        parsed_args = [self._parse_value(a.strip()) for a in self._split_args(args)]

        if name == "len":
            # len(x) -> use a custom operator or var reference
            if len(parsed_args) == 1:
                arg = parsed_args[0]
                if isinstance(arg, dict) and "var" in arg:
                    return {"var": f"_len_{arg['var']}"}
            return {"len": parsed_args[0]}

        if name == "contains":
            # contains(haystack, needle) -> {"in": [needle, haystack]}
            if len(parsed_args) == 2:
                return {"in": [parsed_args[1], parsed_args[0]]}
            raise ValueError("contains() requires 2 arguments")

        if name == "is_empty":
            # is_empty(x) -> {"==": [{"var": "x"}, ""]} or {"!": {"var": "x"}}
            if len(parsed_args) == 1:
                return {"!": parsed_args[0]}
            raise ValueError("is_empty() requires 1 argument")

        if name == "is_null":
            # is_null(x) -> {"==": [{"var": "x"}, null]}
            if len(parsed_args) == 1:
                return {"==": [parsed_args[0], None]}
            raise ValueError("is_null() requires 1 argument")

        if name == "matches":
            # matches(string, pattern) -> custom regex match
            if len(parsed_args) == 2:
                return {"matches": parsed_args}
            raise ValueError("matches() requires 2 arguments")

        return {json_logic_op: parsed_args}

    def _split_by_operator(self, expr: str, operator: str) -> List[str]:
        """Split expression by operator, respecting parentheses."""
        parts = []
        current = []
        depth = 0
        i = 0
        op_len = len(operator)

        while i < len(expr):
            char = expr[i]

            if char == "(":
                depth += 1
                current.append(char)
            elif char == ")":
                depth -= 1
                current.append(char)
            elif depth == 0 and expr[i:i+op_len].upper() == operator.upper():
                # Check for word boundary
                before_ok = i == 0 or not expr[i-1].isalnum()
                after_ok = i + op_len >= len(expr) or not expr[i+op_len].isalnum()
                if before_ok and after_ok:
                    parts.append("".join(current))
                    current = []
                    i += op_len
                    continue
                else:
                    current.append(char)
            else:
                current.append(char)
            i += 1

        parts.append("".join(current))
        return [p for p in parts if p.strip()]

    def _split_args(self, args: str) -> List[str]:
        """Split function arguments by comma, respecting parentheses."""
        result = []
        current = []
        depth = 0

        for char in args:
            if char == "(":
                depth += 1
                current.append(char)
            elif char == ")":
                depth -= 1
                current.append(char)
            elif char == "," and depth == 0:
                result.append("".join(current))
                current = []
            else:
                current.append(char)

        if current:
            result.append("".join(current))

        return result

    def validate(self, expression: str) -> Tuple[bool, Optional[str]]:
        """
        Validate an expression without fully parsing it.

        Returns:
            Tuple of (is_valid, error_message).
        """
        try:
            self.parse(expression)
            return True, None
        except Exception as e:
            return False, str(e)
