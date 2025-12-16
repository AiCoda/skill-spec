"""
Compliance Report Generator.

Generates machine-consumable compliance reports for audit platforms.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from .validator import ValidationResult


REPORT_VERSION = "compliance-report/1.0"
TOOL_VERSION = "1.0.0"


@dataclass
class AuditMetadata:
    """Metadata for audit trail."""

    report_generated_at: str
    tool_version: str
    duration_ms: int
    spec_checksum: Optional[str] = None
    skill_md_checksum: Optional[str] = None
    git_commit: Optional[str] = None
    ci_environment: Optional[Dict[str, str]] = None

    @classmethod
    def generate(
        cls,
        duration_ms: int,
        spec_path: Optional[Path] = None,
        skill_md_path: Optional[Path] = None,
    ) -> "AuditMetadata":
        """Generate audit metadata."""
        metadata = cls(
            report_generated_at=datetime.now(timezone.utc).isoformat(),
            tool_version=TOOL_VERSION,
            duration_ms=duration_ms,
        )

        # Calculate checksums
        if spec_path and spec_path.exists():
            metadata.spec_checksum = _compute_file_checksum(spec_path)

        if skill_md_path and skill_md_path.exists():
            metadata.skill_md_checksum = _compute_file_checksum(skill_md_path)

        # Try to get git commit
        metadata.git_commit = _get_git_commit()

        # Get CI environment if available
        metadata.ci_environment = _get_ci_environment()

        return metadata

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        result = {
            "report_generated_at": self.report_generated_at,
            "tool_version": self.tool_version,
            "duration_ms": self.duration_ms,
        }

        if self.spec_checksum:
            result["spec_checksum"] = self.spec_checksum
        if self.skill_md_checksum:
            result["skill_md_checksum"] = self.skill_md_checksum
        if self.git_commit:
            result["git_commit"] = self.git_commit
        if self.ci_environment:
            result["ci_environment"] = self.ci_environment

        return result


@dataclass
class EvidenceTrace:
    """Evidence trace for audit."""

    policies_applied: List[Dict[str, str]] = field(default_factory=list)
    rules_evaluated: List[Dict[str, Any]] = field(default_factory=list)
    tags_detected: List[Dict[str, Any]] = field(default_factory=list)
    coverage_metrics: Optional[Dict[str, Any]] = None

    @classmethod
    def from_validation_result(cls, result: ValidationResult) -> "EvidenceTrace":
        """Extract evidence trace from validation result."""
        trace = cls()

        # Extract policies applied
        if result.compliance_result:
            for policy in result.compliance_result.policies_checked:
                trace.policies_applied.append({
                    "policy_id": policy,
                    "policy_name": policy,  # Could be enhanced with actual names
                })

            # Extract rules evaluated
            for violation in result.compliance_result.violations:
                trace.rules_evaluated.append({
                    "rule_id": violation.rule_id,
                    "policy_id": violation.policy_id,
                    "result": "fail",
                    "severity": violation.severity,
                    "description": violation.description,
                    "field_path": violation.field_path or "",
                    "required_action": violation.required_action or "",
                })

        # Extract tags detected
        if result.taxonomy_result:
            for tag in result.taxonomy_result.recognized_tags:
                triggered = result.taxonomy_result.triggered_policies.get(tag, [])
                trace.tags_detected.append({
                    "tag": tag,
                    "field_path": "",  # Could be enhanced with actual paths
                    "triggered_policies": triggered,
                })

        # Extract coverage metrics
        if result.coverage_result and result.coverage_result.metrics:
            metrics = result.coverage_result.metrics
            trace.coverage_metrics = {
                "structural_score": metrics.structural_score,
                "behavioral_score": metrics.behavioral_score,
                "failure_modes_covered": metrics.failure_modes_covered,
                "failure_modes_total": metrics.failure_modes_total,
                "decision_rules_referenced": metrics.decision_rules_referenced,
                "decision_rules_total": metrics.decision_rules_total,
            }

        return trace

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        result = {}

        if self.policies_applied:
            result["policies_applied"] = self.policies_applied
        if self.rules_evaluated:
            result["rules_evaluated"] = self.rules_evaluated
        if self.tags_detected:
            result["tags_detected"] = self.tags_detected
        if self.coverage_metrics:
            result["coverage_metrics"] = self.coverage_metrics

        return result


@dataclass
class ComplianceReport:
    """Full compliance report for audit."""

    report_version: str
    skill: Dict[str, str]
    validation: Dict[str, Any]
    evidence_trace: EvidenceTrace
    audit_metadata: AuditMetadata

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "report_version": self.report_version,
            "skill": self.skill,
            "validation": self.validation,
            "evidence_trace": self.evidence_trace.to_dict(),
            "audit_metadata": self.audit_metadata.to_dict(),
        }

    def to_json(self, indent: int = 2) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)

    def to_markdown(self, evidence_report: Optional[Dict[str, Any]] = None) -> str:
        """
        Convert to Markdown format report.

        Args:
            evidence_report: Optional diary evidence data to include in the report.

        Returns:
            Markdown formatted string.
        """
        lines = []
        validation = self.validation
        valid = validation.get("valid", False)
        status = "PASSED" if valid else "FAILED"

        # Header
        lines.append(f"# Validation Report: {self.skill.get('name', 'Unknown')}")
        lines.append("")
        lines.append(f"**Status:** {status}")
        lines.append(f"**Errors:** {validation.get('total_errors', 0)}")
        lines.append(f"**Warnings:** {validation.get('total_warnings', 0)}")
        lines.append("")

        # Summary
        lines.append("## Summary")
        lines.append("")
        summary_parts = []
        if valid:
            summary_parts.append("Validation passed.")
        else:
            summary_parts.append("Validation failed.")
        if validation.get("errors"):
            summary_parts.append(f"Errors: {len(validation['errors'])}")
        if validation.get("warnings"):
            summary_parts.append(f"Warnings: {len(validation['warnings'])}")
        lines.append("```")
        lines.append(" ".join(summary_parts) if summary_parts else "No issues found.")
        lines.append("```")
        lines.append("")

        layers = validation.get("layers", {})

        # Quality Analysis
        quality = layers.get("quality")
        if quality:
            lines.append("## Quality Analysis")
            lines.append("")
            category_counts = quality.get("category_counts", {})
            if category_counts:
                lines.append("| Category | Count |")
                lines.append("|----------|-------|")
                for category, count in category_counts.items():
                    lines.append(f"| {category} | {count} |")
                lines.append("")

            violations = quality.get("violations", [])
            if violations:
                lines.append("### Violations")
                lines.append("")
                for v in violations[:10]:  # Limit to 10
                    lines.append(f"- **{v.get('category', '')}** at `{v.get('path', '')}`: {v.get('pattern', '')}")
                    fix = v.get("fix")
                    if fix:
                        lines.append(f"  - Fix: {fix}")
                lines.append("")

        # Coverage Analysis
        coverage = layers.get("coverage")
        if coverage:
            metrics = coverage.get("metrics", {})
            if metrics:
                lines.append("## Coverage Analysis")
                lines.append("")
                lines.append(f"- **Structural Coverage:** {metrics.get('structural_score', 0)}%")
                lines.append(f"- **Behavioral Coverage:** {metrics.get('behavioral_score', 0)}%")
                lines.append("")

            gaps = coverage.get("gaps", [])
            if gaps:
                lines.append("### Coverage Gaps")
                lines.append("")
                for gap in gaps[:10]:  # Limit to 10
                    lines.append(f"- [{gap.get('severity', '')}] {gap.get('type', '')}: {gap.get('description', '')}")
                lines.append("")

        # Consistency Analysis
        consistency = layers.get("consistency")
        if consistency:
            issues = consistency.get("issues", [])
            orphans = consistency.get("orphans", [])
            if issues or orphans:
                lines.append("## Consistency Analysis")
                lines.append("")
                if issues:
                    lines.append("### Issues")
                    lines.append("")
                    for issue in issues[:10]:
                        lines.append(f"- [{issue.get('severity', '')}] {issue.get('category', '')}: {issue.get('description', '')}")
                    lines.append("")
                if orphans:
                    lines.append("### Orphaned References")
                    lines.append("")
                    for orphan in orphans[:10]:
                        lines.append(f"- {orphan}")
                    lines.append("")

        # Compliance Analysis
        compliance = layers.get("compliance")
        if compliance:
            lines.append("## Compliance Analysis")
            lines.append("")
            policies = compliance.get("policies_checked", [])
            violations = compliance.get("violations", [])
            lines.append(f"- **Policies Checked:** {', '.join(policies) if policies else 'none'}")
            rules_passed = len(policies) - len(violations) if policies else 0
            lines.append(f"- **Rules Passed:** {max(0, rules_passed)}")
            lines.append(f"- **Rules Failed:** {len(violations)}")
            lines.append("")

            if violations:
                lines.append("### Violations")
                lines.append("")
                for v in violations[:10]:  # Limit to 10
                    lines.append(f"- **[{v.get('severity', '')}] {v.get('rule_id', '')}:** {v.get('description', '')}")
                    required = v.get("required_action")
                    if required:
                        lines.append(f"  - Required: {required}")
                lines.append("")

        # Taxonomy Analysis
        taxonomy = layers.get("taxonomy")
        if taxonomy:
            recognized = taxonomy.get("recognized_tags", [])
            tax_violations = taxonomy.get("violations", [])
            if recognized or tax_violations:
                lines.append("## Taxonomy Analysis")
                lines.append("")
                if recognized:
                    lines.append(f"- **Recognized Tags:** {', '.join(recognized)}")
                    lines.append("")
                if tax_violations:
                    lines.append("### Violations")
                    lines.append("")
                    for v in tax_violations[:10]:
                        lines.append(f"- [{v.get('severity', '')}] `{v.get('tag', '')}`: {v.get('message', '')}")
                        suggestion = v.get("suggestion")
                        if suggestion:
                            lines.append(f"  - Suggestion: {suggestion}")
                    lines.append("")

        # Evidence Summary
        if evidence_report:
            lines.append("## Evidence Summary")
            lines.append("")
            summary_data = evidence_report.get("summary", {})
            lines.append(f"- **Total Events:** {summary_data.get('total_events', 0)}")
            lines.append(f"- **Test Runs:** {summary_data.get('test_runs', 0)}")
            lines.append(f"- **Production Runs:** {summary_data.get('production_runs', 0)}")
            success_rate = summary_data.get('success_rate', 0)
            lines.append(f"- **Success Rate:** {success_rate:.1f}%")
            lines.append("")

        # Audit Metadata
        lines.append("## Audit Metadata")
        lines.append("")
        audit = self.audit_metadata.to_dict()
        lines.append(f"- **Generated At:** {audit.get('report_generated_at', '')}")
        lines.append(f"- **Tool Version:** {audit.get('tool_version', '')}")
        lines.append(f"- **Duration:** {audit.get('duration_ms', 0)}ms")
        if audit.get("git_commit"):
            lines.append(f"- **Git Commit:** {audit['git_commit']}")
        if audit.get("spec_checksum"):
            lines.append(f"- **Spec Checksum:** {audit['spec_checksum']}")
        lines.append("")

        return "\n".join(lines)

    def save(self, output_path: Path, format: str = "json") -> None:
        """
        Save report to file.

        Args:
            output_path: Path to save the report.
            format: Output format, either 'json' or 'markdown'.
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)
        if format == "markdown":
            output_path.write_text(self.to_markdown(), encoding="utf-8")
        else:
            output_path.write_text(self.to_json(), encoding="utf-8")


def generate_compliance_report(
    validation_result: ValidationResult,
    skill_name: str,
    skill_version: str,
    skill_path: Path,
    duration_ms: int,
    owner: Optional[str] = None,
) -> ComplianceReport:
    """
    Generate a compliance report from validation results.

    Args:
        validation_result: Result from ValidationEngine.
        skill_name: Skill name.
        skill_version: Skill version.
        skill_path: Path to skill directory.
        duration_ms: Validation duration in milliseconds.
        owner: Skill owner (optional).

    Returns:
        ComplianceReport ready for serialization.
    """
    # Skill info
    skill_info = {
        "name": skill_name,
        "version": skill_version,
        "path": str(skill_path),
    }
    if owner:
        skill_info["owner"] = owner

    # Validation summary
    validation = validation_result.to_dict()

    # Evidence trace
    evidence_trace = EvidenceTrace.from_validation_result(validation_result)

    # Audit metadata
    spec_path = skill_path / "spec.yaml"
    skill_md_path = skill_path / "SKILL.md"
    audit_metadata = AuditMetadata.generate(
        duration_ms=duration_ms,
        spec_path=spec_path if spec_path.exists() else None,
        skill_md_path=skill_md_path if skill_md_path.exists() else None,
    )

    return ComplianceReport(
        report_version=REPORT_VERSION,
        skill=skill_info,
        validation=validation,
        evidence_trace=evidence_trace,
        audit_metadata=audit_metadata,
    )


def _compute_file_checksum(path: Path) -> str:
    """Compute MD5 checksum of a file."""
    hasher = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def _get_git_commit() -> Optional[str]:
    """Get current git commit hash if in a git repo."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            return result.stdout.strip()[:12]  # Short hash
    except (subprocess.SubprocessError, FileNotFoundError):
        pass
    return None


def _get_ci_environment() -> Optional[Dict[str, str]]:
    """Detect CI environment from environment variables."""
    env = {}

    # GitHub Actions
    if os.getenv("GITHUB_ACTIONS"):
        env["ci_provider"] = "github_actions"
        env["build_id"] = os.getenv("GITHUB_RUN_ID", "")
        env["branch"] = os.getenv("GITHUB_REF_NAME", "")
        env["triggered_by"] = os.getenv("GITHUB_ACTOR", "")
        return env

    # GitLab CI
    if os.getenv("GITLAB_CI"):
        env["ci_provider"] = "gitlab_ci"
        env["build_id"] = os.getenv("CI_JOB_ID", "")
        env["branch"] = os.getenv("CI_COMMIT_REF_NAME", "")
        env["triggered_by"] = os.getenv("GITLAB_USER_LOGIN", "")
        return env

    # Jenkins
    if os.getenv("JENKINS_URL"):
        env["ci_provider"] = "jenkins"
        env["build_id"] = os.getenv("BUILD_NUMBER", "")
        env["branch"] = os.getenv("GIT_BRANCH", "")
        env["triggered_by"] = os.getenv("BUILD_USER", "")
        return env

    # CircleCI
    if os.getenv("CIRCLECI"):
        env["ci_provider"] = "circleci"
        env["build_id"] = os.getenv("CIRCLE_BUILD_NUM", "")
        env["branch"] = os.getenv("CIRCLE_BRANCH", "")
        env["triggered_by"] = os.getenv("CIRCLE_USERNAME", "")
        return env

    return None


class ReportTimer:
    """Context manager for timing validation."""

    def __init__(self):
        self.start_time: float = 0
        self.duration_ms: int = 0

    def __enter__(self) -> "ReportTimer":
        self.start_time = time.perf_counter()
        return self

    def __exit__(self, *args):
        self.duration_ms = int((time.perf_counter() - self.start_time) * 1000)
