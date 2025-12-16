"""
Logic engine for Skill-Spec.

Provides expression parsing and evaluation for decision rules.
"""

from .parser import ExpressionParser
from .evaluator import ExpressionEvaluator

__all__ = ["ExpressionParser", "ExpressionEvaluator"]
