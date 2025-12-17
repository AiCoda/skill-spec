"""
Deployment Module for Skill-Spec.

Handles skill deployment bundle creation, target management, and pre-flight checks.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import zipfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

import yaml


@dataclass
class DeploymentTarget:
    """
    A deployment target configuration.

    Attributes:
        name: Target name (e.g., "production", "staging").
        url: Target URL or path.
        auth_type: Authentication type (none, api_key, oauth, etc.).
        env_var: Environment variable containing credentials.
        description: Human-readable description.
    """

    name: str
    url: str
    auth_type: str = "none"
    env_var: Optional[str] = None
    description: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DeploymentTarget":
        """Create from dictionary."""
        return cls(
            name=data["name"],
            url=data["url"],
            auth_type=data.get("auth_type", "none"),
            env_var=data.get("env_var"),
            description=data.get("description", ""),
            metadata=data.get("metadata", {}),
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "url": self.url,
            "auth_type": self.auth_type,
            "env_var": self.env_var,
            "description": self.description,
            "metadata": self.metadata,
        }


@dataclass
class DeploymentBundle:
    """
    A deployment bundle containing skill files and metadata.

    Attributes:
        skill_name: Name of the skill being deployed.
        version: Version of the skill.
        created_at: Bundle creation timestamp.
        files: List of files included in the bundle.
        checksum: Bundle checksum for integrity.
        metadata: Additional deployment metadata.
    """

    skill_name: str
    version: str
    created_at: str
    files: List[str]
    checksum: str
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "skill_name": self.skill_name,
            "version": self.version,
            "created_at": self.created_at,
            "files": self.files,
            "checksum": self.checksum,
            "metadata": self.metadata,
        }


@dataclass
class PreflightCheck:
    """
    A pre-flight check item.

    Attributes:
        name: Check name.
        passed: Whether the check passed.
        message: Status message.
        severity: Check severity (error, warning, info).
    """

    name: str
    passed: bool
    message: str
    severity: str = "error"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "passed": self.passed,
            "message": self.message,
            "severity": self.severity,
        }


@dataclass
class PreflightResult:
    """
    Result of pre-flight checks.

    Attributes:
        success: Overall success status.
        checks: List of individual check results.
        target: Target name if applicable.
    """

    success: bool
    checks: List[PreflightCheck] = field(default_factory=list)
    target: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "success": self.success,
            "target": self.target,
            "checks": [c.to_dict() for c in self.checks],
        }


class TargetRegistry:
    """
    Registry for deployment targets.

    Manages target configurations stored in targets.yaml.
    """

    def __init__(self, targets_path: Path):
        """Initialize with path to targets.yaml."""
        self.targets_path = targets_path
        self._targets: Dict[str, DeploymentTarget] = {}
        self._load_targets()

    def _load_targets(self) -> None:
        """Load targets from YAML file."""
        if not self.targets_path.exists():
            return

        try:
            with open(self.targets_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}

            for name, target_data in data.get("targets", {}).items():
                target_data["name"] = name
                self._targets[name] = DeploymentTarget.from_dict(target_data)
        except yaml.YAMLError:
            pass

    def _save_targets(self) -> None:
        """Save targets to YAML file."""
        self.targets_path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "targets": {
                name: {
                    k: v for k, v in target.to_dict().items()
                    if k != "name" and v  # Skip name and empty values
                }
                for name, target in self._targets.items()
            }
        }

        with open(self.targets_path, "w", encoding="utf-8") as f:
            yaml.dump(data, f, default_flow_style=False, allow_unicode=True)

    def add_target(self, target: DeploymentTarget) -> None:
        """Add or update a target."""
        self._targets[target.name] = target
        self._save_targets()

    def remove_target(self, name: str) -> bool:
        """Remove a target. Returns True if removed."""
        if name in self._targets:
            del self._targets[name]
            self._save_targets()
            return True
        return False

    def get_target(self, name: str) -> Optional[DeploymentTarget]:
        """Get a target by name."""
        return self._targets.get(name)

    def list_targets(self) -> List[DeploymentTarget]:
        """List all targets."""
        return list(self._targets.values())


class BundleCreator:
    """
    Creates deployment bundles for skills.

    Bundle is meant for runtime deployment (e.g., to .claude/skills/).
    Only includes files needed at runtime, NOT spec.yaml which is for
    development and version control only.
    """

    # Files to include in the runtime bundle
    # Note: spec.yaml is intentionally excluded - it's for development only
    BUNDLE_FILES = [
        "SKILL.md",
    ]

    # Resource directories to include if present
    RESOURCE_DIRS = [
        "resources/",
        "scripts/",
    ]

    # Optional files to include if present (with --include-optional)
    OPTIONAL_FILES = [
        "examples/",
        "tests/",
        "README.md",
    ]

    def __init__(self, skill_dir: Path):
        """Initialize with skill directory path."""
        self.skill_dir = skill_dir

    def create_bundle(
        self,
        output_path: Path,
        include_optional: bool = False,
    ) -> DeploymentBundle:
        """
        Create a deployment bundle.

        Args:
            output_path: Path for the output .zip file.
            include_optional: Include optional files (tests, examples).

        Returns:
            DeploymentBundle with bundle metadata.
        """
        # Load skill info
        spec_path = self.skill_dir / "spec.yaml"
        if not spec_path.exists():
            raise FileNotFoundError(f"spec.yaml not found in {self.skill_dir}")

        with open(spec_path, "r", encoding="utf-8") as f:
            spec_data = yaml.safe_load(f) or {}

        skill_info = spec_data.get("skill", {})
        skill_name = skill_info.get("name", self.skill_dir.name)
        version = skill_info.get("version", "1.0.0")

        # Collect files to bundle
        files_to_bundle: List[Path] = []

        # Add required files (SKILL.md)
        for filename in self.BUNDLE_FILES:
            file_path = self.skill_dir / filename
            if file_path.exists():
                files_to_bundle.append(file_path)

        # Add resource directories if present (resources/, scripts/)
        for dirname in self.RESOURCE_DIRS:
            dir_path = self.skill_dir / dirname
            if dir_path.exists() and dir_path.is_dir():
                for f in dir_path.rglob("*"):
                    if f.is_file():
                        files_to_bundle.append(f)

        # Add optional files if requested (tests, examples)
        if include_optional:
            for item in self.OPTIONAL_FILES:
                item_path = self.skill_dir / item
                if item_path.exists():
                    if item_path.is_dir():
                        for f in item_path.rglob("*"):
                            if f.is_file():
                                files_to_bundle.append(f)
                    else:
                        files_to_bundle.append(item_path)

        # Create the bundle
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for file_path in files_to_bundle:
                arcname = file_path.relative_to(self.skill_dir)
                zf.write(file_path, arcname)

        # Calculate checksum
        checksum = self._compute_checksum(output_path)

        # Create bundle metadata
        bundle = DeploymentBundle(
            skill_name=skill_name,
            version=version,
            created_at=datetime.now(timezone.utc).isoformat(),
            files=[str(f.relative_to(self.skill_dir)) for f in files_to_bundle],
            checksum=checksum,
            metadata={
                "bundle_path": str(output_path),
                "skill_dir": str(self.skill_dir),
            },
        )

        # Write manifest
        manifest_path = output_path.with_suffix(".manifest.json")
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(bundle.to_dict(), f, indent=2)

        return bundle

    @staticmethod
    def _compute_checksum(path: Path) -> str:
        """Compute SHA256 checksum of a file."""
        hasher = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                hasher.update(chunk)
        return hasher.hexdigest()[:16]


class PreflightChecker:
    """
    Performs pre-flight checks before deployment.
    """

    def __init__(
        self,
        skill_dir: Path,
        validation_engine: Optional[Any] = None,
    ):
        """Initialize with skill directory and optional validation engine."""
        self.skill_dir = skill_dir
        self.validation_engine = validation_engine

    def run_checks(self, target: Optional[DeploymentTarget] = None) -> PreflightResult:
        """
        Run all pre-flight checks.

        Args:
            target: Optional target to check connectivity.

        Returns:
            PreflightResult with all check results.
        """
        checks = []

        # Check 1: spec.yaml exists
        spec_check = self._check_spec_exists()
        checks.append(spec_check)

        # Check 2: SKILL.md exists
        skill_md_check = self._check_skill_md_exists()
        checks.append(skill_md_check)

        # Check 3: Validation passes
        if self.validation_engine:
            validation_check = self._check_validation()
            checks.append(validation_check)

        # Check 4: Version is specified
        version_check = self._check_version()
        checks.append(version_check)

        # Check 5: No TODO markers in spec
        todo_check = self._check_no_todos()
        checks.append(todo_check)

        # Check 6: Target authentication (if target provided)
        if target:
            auth_check = self._check_target_auth(target)
            checks.append(auth_check)

        # Determine overall success (errors fail, warnings ok)
        success = all(
            c.passed or c.severity != "error"
            for c in checks
        )

        return PreflightResult(
            success=success,
            checks=checks,
            target=target.name if target else None,
        )

    def _check_spec_exists(self) -> PreflightCheck:
        """Check that spec.yaml exists."""
        spec_path = self.skill_dir / "spec.yaml"
        if spec_path.exists():
            return PreflightCheck(
                name="spec_exists",
                passed=True,
                message="spec.yaml exists",
            )
        return PreflightCheck(
            name="spec_exists",
            passed=False,
            message="spec.yaml not found",
        )

    def _check_skill_md_exists(self) -> PreflightCheck:
        """Check that SKILL.md exists."""
        skill_md_path = self.skill_dir / "SKILL.md"
        if skill_md_path.exists():
            return PreflightCheck(
                name="skill_md_exists",
                passed=True,
                message="SKILL.md exists",
            )
        return PreflightCheck(
            name="skill_md_exists",
            passed=False,
            message="SKILL.md not found - run 'skillspec generate'",
        )

    def _check_validation(self) -> PreflightCheck:
        """Check that validation passes."""
        spec_path = self.skill_dir / "spec.yaml"

        if not self.validation_engine:
            return PreflightCheck(
                name="validation",
                passed=True,
                message="Validation skipped (no engine)",
                severity="warning",
            )

        result = self.validation_engine.validate_file(spec_path, strict=False)

        if result.valid:
            return PreflightCheck(
                name="validation",
                passed=True,
                message="Validation passed",
            )

        return PreflightCheck(
            name="validation",
            passed=False,
            message=f"Validation failed: {result.total_errors} errors",
        )

    def _check_version(self) -> PreflightCheck:
        """Check that version is specified."""
        spec_path = self.skill_dir / "spec.yaml"

        try:
            with open(spec_path, "r", encoding="utf-8") as f:
                spec_data = yaml.safe_load(f) or {}

            version = spec_data.get("skill", {}).get("version")
            if version and version != "TODO":
                return PreflightCheck(
                    name="version_specified",
                    passed=True,
                    message=f"Version: {version}",
                )
        except (yaml.YAMLError, IOError):
            pass

        return PreflightCheck(
            name="version_specified",
            passed=False,
            message="Version not specified in skill.version",
            severity="warning",
        )

    def _check_no_todos(self) -> PreflightCheck:
        """Check that no TODO markers remain in spec."""
        spec_path = self.skill_dir / "spec.yaml"

        try:
            content = spec_path.read_text(encoding="utf-8")
            todo_count = content.count("TODO")

            if todo_count == 0:
                return PreflightCheck(
                    name="no_todos",
                    passed=True,
                    message="No TODO markers found",
                )

            return PreflightCheck(
                name="no_todos",
                passed=False,
                message=f"Found {todo_count} TODO markers in spec.yaml",
            )
        except IOError:
            return PreflightCheck(
                name="no_todos",
                passed=False,
                message="Could not read spec.yaml",
            )

    def _check_target_auth(self, target: DeploymentTarget) -> PreflightCheck:
        """Check that target authentication is available."""
        if target.auth_type == "none":
            return PreflightCheck(
                name="target_auth",
                passed=True,
                message="No authentication required",
            )

        if target.env_var:
            if os.getenv(target.env_var):
                return PreflightCheck(
                    name="target_auth",
                    passed=True,
                    message=f"Found credentials in ${target.env_var}",
                )
            return PreflightCheck(
                name="target_auth",
                passed=False,
                message=f"Missing credentials: ${target.env_var} not set",
            )

        return PreflightCheck(
            name="target_auth",
            passed=False,
            message=f"Authentication type '{target.auth_type}' requires env_var",
        )


def create_deployment_bundle(
    skill_dir: Path,
    output_dir: Path,
    include_optional: bool = False,
) -> DeploymentBundle:
    """
    Convenience function to create a deployment bundle.

    Args:
        skill_dir: Path to skill directory.
        output_dir: Output directory for bundle.
        include_optional: Include optional files.

    Returns:
        DeploymentBundle with metadata.
    """
    skill_name = skill_dir.name
    bundle_name = f"{skill_name}-bundle.zip"
    output_path = output_dir / bundle_name

    creator = BundleCreator(skill_dir)
    return creator.create_bundle(output_path, include_optional)


def run_preflight_checks(
    skill_dir: Path,
    target: Optional[DeploymentTarget] = None,
    validation_engine: Optional[Any] = None,
) -> PreflightResult:
    """
    Convenience function to run pre-flight checks.

    Args:
        skill_dir: Path to skill directory.
        target: Optional deployment target.
        validation_engine: Optional validation engine.

    Returns:
        PreflightResult with check results.
    """
    checker = PreflightChecker(skill_dir, validation_engine)
    return checker.run_checks(target)
