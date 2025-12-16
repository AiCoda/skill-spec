"""
Validation Engine.

Combines all validation layers into a unified validation pipeline.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

import yaml

from .schema import SchemaValidator, SchemaValidationResult
from .quality import QualityValidator, QualityValidationResult
from .coverage import CoverageValidator, CoverageValidationResult
from .consistency import ConsistencyValidator, ConsistencyValidationResult
from .compliance import ComplianceValidator, ComplianceValidationResult
from .taxonomy import TaxonomyValidator, TagValidationResult


@dataclass
class ValidationResult:
    """
    Combined result from all validation layers.

    Contains results from:
    - Layer 1: Schema Validation
    - Layer 2: Quality Validation
    - Layer 3: Coverage Validation
    - Layer 4: Consistency Validation
    - Layer 5: Compliance Validation (optional)
    - Tag Taxonomy Validation (optional)
    """

    valid: bool
    schema_result: Optional[SchemaValidationResult] = None
    quality_result: Optional[QualityValidationResult] = None
    coverage_result: Optional[CoverageValidationResult] = None
    consistency_result: Optional[ConsistencyValidationResult] = None
    compliance_result: Optional[ComplianceValidationResult] = None
    taxonomy_result: Optional[TagValidationResult] = None
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    @property
    def total_errors(self) -> int:
        """Total number of errors across all layers."""
        count = len(self.errors)
        if self.schema_result:
            count += len(self.schema_result.errors)
        if self.quality_result:
            count += self.quality_result.total_errors
        if self.coverage_result:
            count += sum(1 for g in self.coverage_result.gaps if g.severity == "error")
        if self.consistency_result:
            count += sum(1 for i in self.consistency_result.issues if i.severity == "error")
        if self.compliance_result:
            count += self.compliance_result.total_errors
        if self.taxonomy_result:
            count += sum(1 for v in self.taxonomy_result.violations if v.severity == "error")
        return count

    @property
    def total_warnings(self) -> int:
        """Total number of warnings across all layers."""
        count = len(self.warnings)
        if self.schema_result:
            count += len(self.schema_result.warnings)
        if self.quality_result:
            count += self.quality_result.total_warnings
        if self.coverage_result:
            count += sum(1 for g in self.coverage_result.gaps if g.severity == "warning")
        if self.consistency_result:
            count += sum(1 for i in self.consistency_result.issues if i.severity == "warning")
        if self.compliance_result:
            count += self.compliance_result.total_warnings
        if self.taxonomy_result:
            count += sum(1 for v in self.taxonomy_result.violations if v.severity == "warning")
        return count

    def summary(self) -> str:
        """Generate a summary of validation results."""
        lines = []
        status = "PASSED" if self.valid else "FAILED"
        lines.append(f"Validation {status}")
        lines.append(f"  Errors: {self.total_errors}")
        lines.append(f"  Warnings: {self.total_warnings}")

        if self.coverage_result and self.coverage_result.metrics:
            metrics = self.coverage_result.metrics
            lines.append(f"  Structural Coverage: {metrics.structural_score}%")
            lines.append(f"  Behavioral Coverage: {metrics.behavioral_score}%")

        if self.compliance_result:
            policies = ", ".join(self.compliance_result.policies_checked) or "none"
            lines.append(f"  Policies Checked: {policies}")

        if self.taxonomy_result:
            recognized = len(self.taxonomy_result.recognized_tags)
            lines.append(f"  Recognized Tags: {recognized}")

        return "\n".join(lines)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON output."""
        result = {
            "valid": self.valid,
            "total_errors": self.total_errors,
            "total_warnings": self.total_warnings,
            "errors": self.errors,
            "warnings": self.warnings,
            "layers": {
                "schema": {
                    "valid": self.schema_result.valid if self.schema_result else None,
                    "errors": [str(e) for e in self.schema_result.errors] if self.schema_result else [],
                    "warnings": [str(w) for w in self.schema_result.warnings] if self.schema_result else [],
                } if self.schema_result else None,
                "quality": {
                    "valid": self.quality_result.valid if self.quality_result else None,
                    "violations": [
                        {
                            "path": v.path,
                            "category": v.category,
                            "severity": v.severity,
                            "pattern": v.pattern,
                            "matched": v.matched_text,
                            "fix": v.fix_suggestion,
                        }
                        for v in self.quality_result.violations
                    ] if self.quality_result else [],
                    "category_counts": self.quality_result.category_counts if self.quality_result else {},
                } if self.quality_result else None,
                "coverage": {
                    "valid": self.coverage_result.valid if self.coverage_result else None,
                    "gaps": [
                        {
                            "type": g.gap_type,
                            "category": g.category,
                            "item": g.item,
                            "description": g.description,
                            "severity": g.severity,
                        }
                        for g in self.coverage_result.gaps
                    ] if self.coverage_result else [],
                    "metrics": {
                        "structural_score": self.coverage_result.metrics.structural_score,
                        "behavioral_score": self.coverage_result.metrics.behavioral_score,
                    } if self.coverage_result else {},
                } if self.coverage_result else None,
                "consistency": {
                    "valid": self.consistency_result.valid if self.consistency_result else None,
                    "issues": [
                        {
                            "category": i.category,
                            "source": i.source,
                            "target": i.target,
                            "description": i.description,
                            "severity": i.severity,
                        }
                        for i in self.consistency_result.issues
                    ] if self.consistency_result else [],
                    "orphans": self.consistency_result.orphans if self.consistency_result else [],
                } if self.consistency_result else None,
                "compliance": {
                    "valid": self.compliance_result.valid if self.compliance_result else None,
                    "policies_checked": self.compliance_result.policies_checked if self.compliance_result else [],
                    "violations": [
                        {
                            "policy_id": v.policy_id,
                            "rule_id": v.rule_id,
                            "category": v.category,
                            "severity": v.severity,
                            "description": v.description,
                            "field_path": v.field_path,
                            "required_action": v.required_action,
                        }
                        for v in self.compliance_result.violations
                    ] if self.compliance_result else [],
                    "category_summary": self.compliance_result.category_summary if self.compliance_result else {},
                } if self.compliance_result else None,
                "taxonomy": {
                    "valid": self.taxonomy_result.valid if self.taxonomy_result else None,
                    "recognized_tags": list(self.taxonomy_result.recognized_tags) if self.taxonomy_result else [],
                    "violations": [
                        {
                            "tag": v.tag,
                            "field_path": v.field_path,
                            "issue_type": v.issue_type,
                            "message": v.message,
                            "suggestion": v.suggestion,
                            "severity": v.severity,
                        }
                        for v in self.taxonomy_result.violations
                    ] if self.taxonomy_result else [],
                    "triggered_policies": self.taxonomy_result.triggered_policies if self.taxonomy_result else {},
                } if self.taxonomy_result else None,
            },
        }
        return result


class ValidationEngine:
    """
    Unified validation engine combining all validation layers.

    Layers:
    - Layer 1: Schema Validation (structure)
    - Layer 2: Quality Validation (forbidden patterns)
    - Layer 3: Coverage Validation (edge cases)
    - Layer 4: Consistency Validation (cross-references)
    - Layer 5: Compliance Validation (enterprise policies - optional)
    - Tag Taxonomy Validation (optional)
    """

    def __init__(
        self,
        schema_path: Optional[Path] = None,
        patterns_dir: Optional[Path] = None,
        languages: Optional[List[str]] = None,
        known_skills: Optional[Set[str]] = None,
        policies_dir: Optional[Path] = None,
        policy_files: Optional[List[Path]] = None,
        taxonomy_dir: Optional[Path] = None,
    ):
        """
        Initialize the validation engine.

        Args:
            schema_path: Path to JSON Schema file.
            patterns_dir: Directory containing pattern YAML files.
            languages: Languages for forbidden patterns.
            known_skills: Set of known skill names for reference validation.
            policies_dir: Directory containing policy YAML files.
            policy_files: List of specific policy files to load.
            taxonomy_dir: Directory containing taxonomy YAML files.
        """
        self.schema_validator = SchemaValidator(schema_path)
        self.quality_validator = QualityValidator(patterns_dir, languages)
        self.coverage_validator = CoverageValidator()
        self.consistency_validator = ConsistencyValidator(known_skills)

        # Layer 5: Compliance Validation (optional)
        self.compliance_validator: Optional[ComplianceValidator] = None
        if policies_dir or policy_files:
            self.compliance_validator = ComplianceValidator()
            if policies_dir:
                self.compliance_validator.load_policies_from_dir(policies_dir)
            if policy_files:
                for policy_file in policy_files:
                    self.compliance_validator.load_policy(policy_file)

        # Tag Taxonomy Validation (optional)
        self.taxonomy_validator: Optional[TaxonomyValidator] = None
        if taxonomy_dir:
            self.taxonomy_validator = TaxonomyValidator()
            self.taxonomy_validator.load_taxonomies_from_dir(taxonomy_dir)

    def validate(
        self,
        spec_data: Dict[str, Any],
        strict: bool = False,
    ) -> ValidationResult:
        """
        Run all validation layers on a spec.

        Args:
            spec_data: The specification data as a dictionary.
            strict: If True, run all layers and fail on any warning.

        Returns:
            ValidationResult with combined results from all layers.
        """
        result = ValidationResult(valid=True)

        # Layer 1: Schema Validation
        result.schema_result = self.schema_validator.validate(spec_data)
        if not result.schema_result.valid:
            result.valid = False
            # Early return if schema is invalid - other layers need valid structure
            return result

        # Layer 2: Quality Validation
        result.quality_result = self.quality_validator.validate(spec_data)
        if not result.quality_result.valid:
            result.valid = False

        # Layer 3: Coverage Validation
        result.coverage_result = self.coverage_validator.validate(spec_data)
        if not result.coverage_result.valid:
            result.valid = False

        # Layer 4: Consistency Validation
        result.consistency_result = self.consistency_validator.validate(spec_data)
        if not result.consistency_result.valid:
            result.valid = False

        # Layer 5: Compliance Validation (optional)
        if self.compliance_validator:
            result.compliance_result = self.compliance_validator.validate(spec_data)
            if not result.compliance_result.valid:
                result.valid = False

        # Tag Taxonomy Validation (optional)
        if self.taxonomy_validator:
            result.taxonomy_result = self.taxonomy_validator.validate(spec_data)
            if not result.taxonomy_result.valid:
                result.valid = False

        # In strict mode, warnings also cause failure
        if strict and result.total_warnings > 0:
            result.valid = False

        return result

    def validate_file(
        self,
        path: Path,
        strict: bool = False,
    ) -> ValidationResult:
        """
        Validate a YAML file.

        Args:
            path: Path to the spec.yaml file.
            strict: If True, fail on warnings.

        Returns:
            ValidationResult with combined results.
        """
        result = ValidationResult(valid=True)

        if not path.exists():
            result.valid = False
            result.errors.append(f"File not found: {path}")
            return result

        try:
            with open(path, "r", encoding="utf-8") as f:
                spec_data = yaml.safe_load(f)
        except yaml.YAMLError as e:
            result.valid = False
            result.errors.append(f"YAML parse error: {e}")
            return result

        if spec_data is None:
            result.valid = False
            result.errors.append("File is empty")
            return result

        return self.validate(spec_data, strict=strict)

    def quick_validate(self, spec_data: Dict[str, Any]) -> bool:
        """
        Quick validation check (schema only).

        Args:
            spec_data: The specification data.

        Returns:
            True if schema is valid.
        """
        result = self.schema_validator.validate(spec_data)
        return result.valid


def validate_spec(
    spec_path: Path,
    strict: bool = False,
    schema_path: Optional[Path] = None,
    patterns_dir: Optional[Path] = None,
    policies_dir: Optional[Path] = None,
    policy_files: Optional[List[Path]] = None,
    taxonomy_dir: Optional[Path] = None,
) -> ValidationResult:
    """
    Convenience function to validate a spec file.

    Args:
        spec_path: Path to the spec.yaml file.
        strict: If True, fail on warnings.
        schema_path: Optional path to JSON Schema.
        patterns_dir: Optional path to patterns directory.
        policies_dir: Directory containing policy YAML files.
        policy_files: List of specific policy files to load.
        taxonomy_dir: Directory containing taxonomy YAML files.

    Returns:
        ValidationResult with combined results.
    """
    engine = ValidationEngine(
        schema_path=schema_path,
        patterns_dir=patterns_dir,
        policies_dir=policies_dir,
        policy_files=policy_files,
        taxonomy_dir=taxonomy_dir,
    )
    return engine.validate_file(spec_path, strict=strict)
