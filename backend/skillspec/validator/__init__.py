"""
Skill-Spec Validation Engine.

This package provides multi-layer validation for skill specifications:
- Layer 1: Schema Validation (structure and required fields)
- Layer 2: Quality Validation (forbidden patterns, expression parsing)
- Layer 3: Coverage Validation (decision rules coverage, edge cases)
- Layer 4: Consistency Validation (cross-reference checks)
- Layer 5: Compliance Validation (enterprise policies - optional)
- Tag Taxonomy: Input tag classification and policy triggers
"""

from .schema import SchemaValidator, SchemaValidationResult
from .quality import QualityValidator, QualityValidationResult
from .coverage import CoverageValidator, CoverageValidationResult
from .consistency import ConsistencyValidator, ConsistencyValidationResult
from .compliance import (
    ComplianceValidator,
    ComplianceValidationResult,
    Policy,
    PolicyRule,
    PolicyViolation,
)
from .taxonomy import (
    TaxonomyValidator,
    TagValidationResult,
    Taxonomy,
    Tag,
    TagViolation,
)
from .engine import ValidationEngine, ValidationResult
from .anthropic_format import (
    AnthropicFormatValidator,
    AnthropicFormatResult,
    FrontmatterValidation,
    SectionValidation,
    SectionRequirement,
    validate_skill_md,
)
from .constraints import (
    StringConstraintValidator,
    ConstraintValidationResult,
    ConstraintViolation,
    validate_constraints,
    validate_input_value,
)

__all__ = [
    # Layer 1: Schema
    "SchemaValidator",
    "SchemaValidationResult",
    # Layer 2: Quality
    "QualityValidator",
    "QualityValidationResult",
    # Layer 3: Coverage
    "CoverageValidator",
    "CoverageValidationResult",
    # Layer 4: Consistency
    "ConsistencyValidator",
    "ConsistencyValidationResult",
    # Layer 5: Compliance
    "ComplianceValidator",
    "ComplianceValidationResult",
    "Policy",
    "PolicyRule",
    "PolicyViolation",
    # Tag Taxonomy
    "TaxonomyValidator",
    "TagValidationResult",
    "Taxonomy",
    "Tag",
    "TagViolation",
    # Engine
    "ValidationEngine",
    "ValidationResult",
    # Anthropic Format
    "AnthropicFormatValidator",
    "AnthropicFormatResult",
    "FrontmatterValidation",
    "SectionValidation",
    "SectionRequirement",
    "validate_skill_md",
    # String Constraints
    "StringConstraintValidator",
    "ConstraintValidationResult",
    "ConstraintViolation",
    "validate_constraints",
    "validate_input_value",
]
