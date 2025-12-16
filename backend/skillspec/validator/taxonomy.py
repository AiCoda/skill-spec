"""
Tag Taxonomy Validation System.

Validates input tags against defined taxonomies and triggers policy checks.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from difflib import get_close_matches
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import yaml


@dataclass
class TagViolation:
    """Represents a tag validation issue."""

    tag: str
    field_path: str
    issue_type: str  # unknown | deprecated | exclusive | depth_exceeded
    message: str
    suggestion: Optional[str] = None
    severity: str = "warning"


@dataclass
class TagValidationResult:
    """Result of tag taxonomy validation."""

    valid: bool
    violations: List[TagViolation] = field(default_factory=list)
    recognized_tags: Set[str] = field(default_factory=set)
    triggered_policies: Dict[str, List[str]] = field(default_factory=dict)

    def add_violation(self, violation: TagViolation) -> None:
        self.violations.append(violation)
        if violation.severity == "error":
            self.valid = False


@dataclass
class Tag:
    """A single tag definition."""

    id: str
    description: str
    inherits: List[str] = field(default_factory=list)
    policies: List[str] = field(default_factory=list)
    deprecated: bool = False
    replacement: Optional[str] = None


@dataclass
class Taxonomy:
    """A complete taxonomy definition."""

    id: str
    name: str
    version: str
    description: str
    tags: Dict[str, Tag] = field(default_factory=dict)
    constraints: Dict[str, Any] = field(default_factory=dict)
    policy_triggers: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    @classmethod
    def from_yaml(cls, yaml_content: str) -> "Taxonomy":
        """Load taxonomy from YAML content."""
        data = yaml.safe_load(yaml_content)
        taxonomy_data = data.get("taxonomy", {})

        # Parse tags from categories
        tags = {}
        for category_name, category_data in data.get("categories", {}).items():
            for tag_data in category_data.get("tags", []):
                tag_id = tag_data.get("id", "")
                tags[tag_id] = Tag(
                    id=tag_id,
                    description=tag_data.get("description", ""),
                    inherits=tag_data.get("inherits", []),
                    policies=tag_data.get("policies", []),
                    deprecated=tag_data.get("deprecated", False),
                    replacement=tag_data.get("replacement"),
                )
            # Also add the category itself as a tag
            tags[category_name] = Tag(
                id=category_name,
                description=category_data.get("description", ""),
                inherits=[],
                policies=[],
            )

        return cls(
            id=taxonomy_data.get("id", "unknown"),
            name=taxonomy_data.get("name", "Unknown Taxonomy"),
            version=taxonomy_data.get("version", "1.0.0"),
            description=taxonomy_data.get("description", ""),
            tags=tags,
            constraints=data.get("constraints", {}),
            policy_triggers=data.get("policy_triggers", {}),
        )

    @classmethod
    def from_file(cls, path: Path) -> "Taxonomy":
        """Load taxonomy from a file."""
        with open(path, "r", encoding="utf-8") as f:
            return cls.from_yaml(f.read())

    def get_all_tag_ids(self) -> Set[str]:
        """Get all valid tag IDs including wildcards."""
        tag_ids = set(self.tags.keys())
        # Add wildcard patterns
        for tag_id in list(tag_ids):
            if ":" in tag_id:
                prefix = tag_id.split(":")[0]
                tag_ids.add(f"{prefix}:*")
        return tag_ids

    def resolve_inheritance(self, tag_id: str) -> List[str]:
        """Resolve full inheritance chain for a tag."""
        if tag_id not in self.tags:
            return []

        result = [tag_id]
        visited = {tag_id}
        queue = list(self.tags[tag_id].inherits)

        while queue:
            parent = queue.pop(0)
            if parent in visited:
                continue
            visited.add(parent)
            result.append(parent)
            if parent in self.tags:
                queue.extend(self.tags[parent].inherits)

        return result

    def get_policies_for_tag(self, tag_id: str) -> List[str]:
        """Get all policies triggered by a tag (including inherited)."""
        policies = []
        for resolved_tag in self.resolve_inheritance(tag_id):
            if resolved_tag in self.tags:
                policies.extend(self.tags[resolved_tag].policies)
        return list(set(policies))


class TaxonomyValidator:
    """
    Validates tags against taxonomies.

    Features:
    - Tag whitelist validation
    - Unknown tag detection with suggestions
    - Tag inheritance validation
    - Policy trigger mapping
    """

    def __init__(self, taxonomies: Optional[List[Taxonomy]] = None):
        """
        Initialize the taxonomy validator.

        Args:
            taxonomies: List of taxonomies to validate against.
        """
        self.taxonomies = taxonomies or []
        self._all_tags: Optional[Set[str]] = None

    @property
    def all_tags(self) -> Set[str]:
        """Get all valid tags from all taxonomies."""
        if self._all_tags is None:
            self._all_tags = set()
            for taxonomy in self.taxonomies:
                self._all_tags.update(taxonomy.get_all_tag_ids())
        return self._all_tags

    def load_taxonomy(self, path: Path) -> None:
        """Load and add a taxonomy from file."""
        taxonomy = Taxonomy.from_file(path)
        self.taxonomies.append(taxonomy)
        self._all_tags = None  # Reset cache

    def load_taxonomies_from_dir(self, directory: Path) -> None:
        """Load all taxonomies from a directory."""
        if not directory.exists():
            return

        for file_path in directory.glob("*.yaml"):
            try:
                self.load_taxonomy(file_path)
            except Exception:
                pass  # Skip invalid taxonomy files

    def validate(self, spec_data: Dict[str, Any]) -> TagValidationResult:
        """
        Validate tags in a specification.

        Args:
            spec_data: The specification data.

        Returns:
            TagValidationResult with validation status.
        """
        result = TagValidationResult(valid=True)

        # Extract tags from inputs
        inputs = spec_data.get("inputs", [])
        for i, inp in enumerate(inputs):
            tags = inp.get("tags", [])
            for tag in tags:
                self._validate_tag(tag, f"inputs[{i}].tags", result)

        return result

    def _validate_tag(
        self,
        tag: str,
        field_path: str,
        result: TagValidationResult
    ) -> None:
        """Validate a single tag."""
        # Check if tag is known
        if tag not in self.all_tags and not self._matches_wildcard(tag):
            # Find suggestions
            suggestions = get_close_matches(tag, list(self.all_tags), n=3, cutoff=0.6)
            suggestion_text = f"Did you mean: {', '.join(suggestions)}?" if suggestions else None

            result.add_violation(TagViolation(
                tag=tag,
                field_path=field_path,
                issue_type="unknown",
                message=f"Unknown tag: {tag}",
                suggestion=suggestion_text,
                severity="warning"
            ))
            return

        result.recognized_tags.add(tag)

        # Check for deprecation
        for taxonomy in self.taxonomies:
            if tag in taxonomy.tags:
                tag_def = taxonomy.tags[tag]
                if tag_def.deprecated:
                    result.add_violation(TagViolation(
                        tag=tag,
                        field_path=field_path,
                        issue_type="deprecated",
                        message=f"Tag '{tag}' is deprecated",
                        suggestion=f"Use '{tag_def.replacement}' instead" if tag_def.replacement else None,
                        severity="warning"
                    ))

                # Check inheritance depth
                inheritance_chain = taxonomy.resolve_inheritance(tag)
                max_depth = taxonomy.constraints.get("max_inheritance_depth", 3)
                if len(inheritance_chain) > max_depth:
                    result.add_violation(TagViolation(
                        tag=tag,
                        field_path=field_path,
                        issue_type="depth_exceeded",
                        message=f"Tag inheritance depth ({len(inheritance_chain)}) exceeds maximum ({max_depth})",
                        severity="warning"
                    ))

                # Collect triggered policies
                policies = taxonomy.get_policies_for_tag(tag)
                if policies:
                    result.triggered_policies[tag] = policies

    def _matches_wildcard(self, tag: str) -> bool:
        """Check if tag matches any wildcard pattern."""
        if ":" not in tag:
            return False

        prefix = tag.split(":")[0]
        wildcard = f"{prefix}:*"
        return wildcard in self.all_tags

    def get_policy_triggers(
        self,
        spec_data: Dict[str, Any]
    ) -> Dict[str, List[Tuple[str, str]]]:
        """
        Get all policy triggers for a spec.

        Returns dict of policy_id -> list of (tag, field_path) tuples.
        """
        triggers: Dict[str, List[Tuple[str, str]]] = {}

        inputs = spec_data.get("inputs", [])
        for i, inp in enumerate(inputs):
            tags = inp.get("tags", [])
            field_path = f"inputs[{i}]"

            for tag in tags:
                for taxonomy in self.taxonomies:
                    policies = taxonomy.get_policies_for_tag(tag)
                    for policy in policies:
                        if policy not in triggers:
                            triggers[policy] = []
                        triggers[policy].append((tag, field_path))

        return triggers
