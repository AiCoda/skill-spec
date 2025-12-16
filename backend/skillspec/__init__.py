"""
Skill-Spec: Spec-driven skill development framework.

This package provides tools for creating, validating, and managing
skill specifications using a structured, spec-first approach.
"""

from .models import (
    SkillSpec,
    SkillMetadata,
    InputSpec,
    InputDomain,
    DecisionRule,
    DecisionRulesConfig,
    ExecutionStep,
    OutputContract,
    FailureMode,
    EdgeCase,
    ContextInfo,
    Example,
    MetaConfig,
)

__version__ = "1.0.0"
__all__ = [
    "SkillSpec",
    "SkillMetadata",
    "InputSpec",
    "InputDomain",
    "DecisionRule",
    "DecisionRulesConfig",
    "ExecutionStep",
    "OutputContract",
    "FailureMode",
    "EdgeCase",
    "ContextInfo",
    "Example",
    "MetaConfig",
]
