"""
Migration System for Converting SKILL.md to Spec-Driven Format.

This module provides functionality for migrating existing SKILL.md files
to the spec.yaml format used by the Skill-Spec system.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml


@dataclass
class FrontmatterData:
    """
    Parsed frontmatter data from a SKILL.md file.

    Attributes:
        name: Skill name from frontmatter.
        description: Skill description.
        raw: Raw frontmatter dictionary.
    """

    name: str = ""
    description: str = ""
    raw: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MarkdownSection:
    """
    A section extracted from a Markdown file.

    Attributes:
        title: Section title (without ## prefix).
        level: Heading level (1-6).
        content: Raw content of the section.
        subsections: List of nested subsections.
    """

    title: str
    level: int
    content: str
    subsections: List["MarkdownSection"] = field(default_factory=list)


@dataclass
class MigrationResult:
    """
    Result of migrating a SKILL.md file.

    Attributes:
        success: Whether migration completed.
        spec_data: Generated spec.yaml data.
        warnings: List of warnings during migration.
        todos: List of items that need manual attention.
        guide: Migration guide text.
    """

    success: bool
    spec_data: Dict[str, Any] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)
    todos: List[str] = field(default_factory=list)
    guide: str = ""


class FrontmatterParser:
    """Parser for YAML frontmatter in Markdown files."""

    FRONTMATTER_PATTERN = re.compile(
        r"^---\s*\n(.*?)\n---\s*\n",
        re.MULTILINE | re.DOTALL,
    )

    @classmethod
    def parse(cls, content: str) -> Tuple[FrontmatterData, str]:
        """
        Parse frontmatter from Markdown content.

        Args:
            content: Full Markdown file content.

        Returns:
            Tuple of (FrontmatterData, remaining content).
        """
        match = cls.FRONTMATTER_PATTERN.match(content)

        if not match:
            return FrontmatterData(), content

        try:
            raw_data = yaml.safe_load(match.group(1)) or {}
        except yaml.YAMLError:
            return FrontmatterData(), content

        remaining = content[match.end():]

        return FrontmatterData(
            name=raw_data.get("name", ""),
            description=raw_data.get("description", ""),
            raw=raw_data,
        ), remaining


class MarkdownSectionExtractor:
    """Extracts sections from Markdown content."""

    HEADING_PATTERN = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)

    @classmethod
    def extract(cls, content: str) -> List[MarkdownSection]:
        """
        Extract all sections from Markdown content.

        Args:
            content: Markdown content (without frontmatter).

        Returns:
            List of top-level sections with nested subsections.
        """
        # Find all headings
        headings = []
        for match in cls.HEADING_PATTERN.finditer(content):
            level = len(match.group(1))
            title = match.group(2).strip()
            start = match.start()
            end = match.end()
            headings.append({
                "level": level,
                "title": title,
                "start": start,
                "content_start": end,
            })

        if not headings:
            return []

        # Extract content between headings
        sections = []
        for i, heading in enumerate(headings):
            if i + 1 < len(headings):
                content_end = headings[i + 1]["start"]
            else:
                content_end = len(content)

            section_content = content[heading["content_start"]:content_end].strip()

            sections.append(MarkdownSection(
                title=heading["title"],
                level=heading["level"],
                content=section_content,
            ))

        # Build hierarchy
        return cls._build_hierarchy(sections)

    @classmethod
    def _build_hierarchy(
        cls,
        flat_sections: List[MarkdownSection],
    ) -> List[MarkdownSection]:
        """Build section hierarchy from flat list."""
        if not flat_sections:
            return []

        result = []
        stack: List[MarkdownSection] = []

        for section in flat_sections:
            # Pop sections of same or higher level
            while stack and stack[-1].level >= section.level:
                stack.pop()

            if stack:
                stack[-1].subsections.append(section)
            else:
                result.append(section)

            stack.append(section)

        return result

    @classmethod
    def get_section(
        cls,
        sections: List[MarkdownSection],
        title: str,
    ) -> Optional[MarkdownSection]:
        """Find a section by title (case-insensitive)."""
        title_lower = title.lower()

        for section in sections:
            if section.title.lower() == title_lower:
                return section
            # Check subsections
            found = cls.get_section(section.subsections, title)
            if found:
                return found

        return None


class SkillMigrator:
    """
    Migrates SKILL.md files to spec.yaml format.

    This class handles the conversion of existing SKILL.md files to the
    spec-driven format, preserving as much information as possible and
    marking areas that need manual attention.
    """

    # Section mappings from SKILL.md to spec.yaml
    SECTION_MAPPINGS = {
        "purpose": ["purpose", "description", "overview"],
        "inputs": ["inputs", "parameters", "arguments"],
        "prerequisites": ["prerequisites", "requirements", "setup"],
        "non_goals": [
            "non-goals",
            "non goals",
            "what this skill does not do",
            "limitations",
            "out of scope",
        ],
        "workflow": ["workflow", "steps", "process", "how it works"],
        "edge_cases": ["edge cases", "special cases", "edge-cases"],
        "output_format": ["output format", "output", "returns"],
        "error_handling": [
            "error handling",
            "errors",
            "failure modes",
            "error-handling",
        ],
        "works_with": ["works well with", "related skills", "see also"],
    }

    def __init__(self):
        """Initialize the migrator."""
        self.frontmatter_parser = FrontmatterParser()
        self.section_extractor = MarkdownSectionExtractor()

    def migrate(self, skill_md_path: Path) -> MigrationResult:
        """
        Migrate a SKILL.md file to spec.yaml format.

        Args:
            skill_md_path: Path to the SKILL.md file.

        Returns:
            MigrationResult with generated spec data.
        """
        result = MigrationResult(success=True)

        if not skill_md_path.exists():
            result.success = False
            result.warnings.append(f"File not found: {skill_md_path}")
            return result

        content = skill_md_path.read_text(encoding="utf-8")

        # Parse frontmatter
        frontmatter, body = self.frontmatter_parser.parse(content)

        # Extract sections
        sections = self.section_extractor.extract(body)

        # Build spec data
        spec_data = self._build_spec_data(frontmatter, sections, result)
        result.spec_data = spec_data

        # Generate migration guide
        result.guide = self._generate_guide(result)

        return result

    def _build_spec_data(
        self,
        frontmatter: FrontmatterData,
        sections: List[MarkdownSection],
        result: MigrationResult,
    ) -> Dict[str, Any]:
        """Build spec.yaml data from parsed content."""
        spec_data: Dict[str, Any] = {
            "spec_version": "skill-spec/1.0",
        }

        # Build skill section
        skill_name = self._extract_skill_name(frontmatter, sections)
        spec_data["skill"] = {
            "name": skill_name or "TODO-skill-name",
            "version": "1.0.0",
            "purpose": self._extract_purpose(frontmatter, sections, result),
            "owner": "TODO-owner",
        }

        if not skill_name:
            result.todos.append("Set skill name in skill.name")

        # Build inputs section
        spec_data["inputs"] = self._extract_inputs(sections, result)

        # Build preconditions section
        spec_data["preconditions"] = self._extract_preconditions(sections, result)

        # Build non_goals section
        spec_data["non_goals"] = self._extract_non_goals(sections, result)

        # Build decision_rules section (always needs manual work)
        spec_data["decision_rules"] = self._create_default_decision_rules(result)

        # Build steps section
        spec_data["steps"] = self._extract_steps(sections, result)

        # Build output_contract section
        spec_data["output_contract"] = self._extract_output_contract(sections, result)

        # Build failure_modes section
        spec_data["failure_modes"] = self._extract_failure_modes(sections, result)

        # Build edge_cases section
        spec_data["edge_cases"] = self._extract_edge_cases(sections, result)

        # Build context section
        context = self._extract_context(sections, result)
        if context:
            spec_data["context"] = context

        return spec_data

    def _extract_skill_name(
        self,
        frontmatter: FrontmatterData,
        sections: List[MarkdownSection],
    ) -> str:
        """Extract skill name from frontmatter or title."""
        if frontmatter.name:
            return frontmatter.name

        # Try to get from H1 title
        for section in sections:
            if section.level == 1:
                # Convert title to kebab-case
                name = section.title.lower()
                name = re.sub(r"[^a-z0-9]+", "-", name)
                name = name.strip("-")
                return name

        return ""

    def _extract_purpose(
        self,
        frontmatter: FrontmatterData,
        sections: List[MarkdownSection],
        result: MigrationResult,
    ) -> str:
        """Extract purpose from description or purpose section."""
        if frontmatter.description:
            # Remove "Use when:" suffix if present
            desc = re.sub(r"\s*Use when:.*$", "", frontmatter.description, flags=re.I)
            return desc.strip()

        # Look for purpose section
        for title in self.SECTION_MAPPINGS["purpose"]:
            section = self.section_extractor.get_section(sections, title)
            if section and section.content:
                # Take first paragraph
                first_para = section.content.split("\n\n")[0]
                return first_para.strip()

        result.todos.append("Define skill purpose in skill.purpose")
        return "TODO: Define skill purpose"

    def _extract_inputs(
        self,
        sections: List[MarkdownSection],
        result: MigrationResult,
    ) -> List[Dict[str, Any]]:
        """Extract inputs from inputs section."""
        inputs = []

        for title in self.SECTION_MAPPINGS["inputs"]:
            section = self.section_extractor.get_section(sections, title)
            if section:
                # Parse list items
                items = self._parse_list_items(section.content)
                for item in items:
                    input_spec = self._parse_input_item(item)
                    if input_spec:
                        inputs.append(input_spec)
                break

        if not inputs:
            result.todos.append("Define inputs in inputs section")
            inputs.append({
                "name": "TODO_input",
                "type": "string",
                "required": True,
                "description": "TODO: Define input",
            })

        return inputs

    def _parse_input_item(self, item: str) -> Optional[Dict[str, Any]]:
        """Parse a single input item from markdown list."""
        # Try to parse: **name** (type, required/optional) - description
        match = re.match(
            r"\*\*(\w+)\*\*\s*\(([^)]+)\)(?:\s*[-:]?\s*(.*))?",
            item,
            re.IGNORECASE,
        )

        if match:
            name = match.group(1)
            type_info = match.group(2).lower()
            description = match.group(3) or ""

            # Determine type and required
            input_type = "string"
            required = True

            if "int" in type_info or "number" in type_info:
                input_type = "integer"
            elif "bool" in type_info:
                input_type = "boolean"
            elif "array" in type_info or "list" in type_info:
                input_type = "array"
            elif "object" in type_info:
                input_type = "object"

            if "optional" in type_info:
                required = False

            return {
                "name": name,
                "type": input_type,
                "required": required,
                "description": description.strip() if description else f"TODO: Define {name}",
            }

        # Simple format: name - description
        match = re.match(r"(\w+)\s*[-:]\s*(.*)", item)
        if match:
            return {
                "name": match.group(1),
                "type": "string",
                "required": True,
                "description": match.group(2).strip() or "TODO: Define",
            }

        return None

    def _extract_preconditions(
        self,
        sections: List[MarkdownSection],
        result: MigrationResult,
    ) -> List[str]:
        """Extract preconditions from prerequisites section."""
        for title in self.SECTION_MAPPINGS["prerequisites"]:
            section = self.section_extractor.get_section(sections, title)
            if section:
                items = self._parse_list_items(section.content)
                if items:
                    return items

        result.todos.append("Define preconditions")
        return ["TODO: Define preconditions"]

    def _extract_non_goals(
        self,
        sections: List[MarkdownSection],
        result: MigrationResult,
    ) -> List[str]:
        """Extract non-goals from limitations section."""
        for title in self.SECTION_MAPPINGS["non_goals"]:
            section = self.section_extractor.get_section(sections, title)
            if section:
                items = self._parse_list_items(section.content)
                if items:
                    return items

        result.todos.append("Define non_goals (what is out of scope)")
        return ["TODO: Define what is out of scope"]

    def _create_default_decision_rules(
        self,
        result: MigrationResult,
    ) -> Dict[str, Any]:
        """Create default decision rules placeholder."""
        result.todos.append("Define decision_rules based on skill logic")
        return {
            "_config": {
                "match_strategy": "first_match",
                "conflict_resolution": "error",
            },
            "rules": [{
                "id": "rule_default",
                "is_default": True,
                "when": True,
                "then": {
                    "status": "success",
                    "path": "default",
                },
            }],
        }

    def _extract_steps(
        self,
        sections: List[MarkdownSection],
        result: MigrationResult,
    ) -> List[Dict[str, Any]]:
        """Extract workflow steps."""
        steps = []

        for title in self.SECTION_MAPPINGS["workflow"]:
            section = self.section_extractor.get_section(sections, title)
            if section:
                items = self._parse_list_items(section.content)
                for i, item in enumerate(items, 1):
                    # Clean up the item text
                    action = re.sub(r"^\d+\.\s*", "", item)
                    action = re.sub(r"\*\*([^*]+)\*\*", r"\1", action)
                    step_id = f"step_{i}"
                    steps.append({
                        "id": step_id,
                        "action": action[:100] if len(action) > 100 else action,
                        "output": f"result_{i}",
                    })
                break

        if not steps:
            result.todos.append("Define workflow steps")
            steps.append({
                "id": "step_1",
                "action": "TODO: Define main action",
                "output": "result",
            })

        return steps

    def _extract_output_contract(
        self,
        sections: List[MarkdownSection],
        result: MigrationResult,
    ) -> Dict[str, Any]:
        """Extract output contract."""
        for title in self.SECTION_MAPPINGS["output_format"]:
            section = self.section_extractor.get_section(sections, title)
            if section:
                # Try to extract JSON schema from code block
                code_match = re.search(
                    r"```(?:json)?\s*\n(.*?)\n```",
                    section.content,
                    re.DOTALL,
                )
                if code_match:
                    try:
                        schema = yaml.safe_load(code_match.group(1))
                        if isinstance(schema, dict):
                            return {
                                "format": "json",
                                "schema": schema,
                            }
                    except yaml.YAMLError:
                        pass

        result.todos.append("Define output_contract schema")
        return {
            "format": "json",
            "schema": {
                "type": "object",
                "required": ["status"],
                "properties": {
                    "status": {"enum": ["success", "error"]},
                },
            },
        }

    def _extract_failure_modes(
        self,
        sections: List[MarkdownSection],
        result: MigrationResult,
    ) -> List[Dict[str, Any]]:
        """Extract failure modes from error handling section."""
        modes = []

        for title in self.SECTION_MAPPINGS["error_handling"]:
            section = self.section_extractor.get_section(sections, title)
            if section:
                items = self._parse_list_items(section.content)
                for item in items:
                    # Try to parse: **CODE**: description
                    match = re.match(r"\*\*(\w+)\*\*:?\s*(.*)", item)
                    if match:
                        code = match.group(1).upper()
                        desc = match.group(2).strip()
                        retryable = "retry" in desc.lower()
                        modes.append({
                            "code": code,
                            "retryable": retryable,
                            "description": desc or f"TODO: Describe {code}",
                        })
                break

        if not modes:
            result.todos.append("Define failure_modes")
            modes.append({
                "code": "VALIDATION_ERROR",
                "retryable": False,
                "description": "TODO: Define validation error",
            })

        return modes

    def _extract_edge_cases(
        self,
        sections: List[MarkdownSection],
        result: MigrationResult,
    ) -> List[Dict[str, Any]]:
        """Extract edge cases."""
        cases = []

        for title in self.SECTION_MAPPINGS["edge_cases"]:
            section = self.section_extractor.get_section(sections, title)
            if section:
                items = self._parse_list_items(section.content)
                for item in items:
                    # Try to parse: **case**: expected
                    match = re.match(r"\*\*([^*]+)\*\*:?\s*(.*)", item)
                    if match:
                        case_name = match.group(1).strip()
                        expected = match.group(2).strip()
                        cases.append({
                            "case": case_name,
                            "expected": {
                                "status": "TODO",
                                "description": expected or "TODO: Define expected",
                            },
                        })
                    else:
                        cases.append({
                            "case": item[:50],
                            "expected": {"status": "TODO"},
                        })
                break

        if not cases:
            result.todos.append("Define edge_cases")
            cases.append({
                "case": "empty_input",
                "expected": {"status": "error", "code": "VALIDATION_ERROR"},
            })

        return cases

    def _extract_context(
        self,
        sections: List[MarkdownSection],
        result: MigrationResult,
    ) -> Optional[Dict[str, Any]]:
        """Extract context information."""
        context: Dict[str, Any] = {}

        for title in self.SECTION_MAPPINGS["works_with"]:
            section = self.section_extractor.get_section(sections, title)
            if section:
                items = self._parse_list_items(section.content)
                works_with = []
                for item in items:
                    # Try to parse: **skill-name**: reason
                    match = re.match(r"\*\*([^*]+)\*\*:?\s*(.*)", item)
                    if match:
                        works_with.append({
                            "skill": match.group(1).strip(),
                            "reason": match.group(2).strip() or "TODO: Explain",
                        })
                if works_with:
                    context["works_with"] = works_with
                break

        return context if context else None

    def _parse_list_items(self, content: str) -> List[str]:
        """Parse list items from markdown content."""
        items = []

        # Match both - and * list markers, and numbered lists
        pattern = re.compile(r"^\s*(?:[-*]|\d+\.)\s+(.+)$", re.MULTILINE)

        for match in pattern.finditer(content):
            item = match.group(1).strip()
            if item:
                items.append(item)

        return items

    def _generate_guide(self, result: MigrationResult) -> str:
        """Generate migration guide text."""
        lines = [
            "Migration Guide",
            "=" * 40,
            "",
            "The following spec.yaml has been generated from your SKILL.md file.",
            "",
        ]

        if result.todos:
            lines.append("Items requiring attention:")
            lines.append("-" * 40)
            for i, todo in enumerate(result.todos, 1):
                lines.append(f"  {i}. {todo}")
            lines.append("")

        if result.warnings:
            lines.append("Warnings:")
            lines.append("-" * 40)
            for warning in result.warnings:
                lines.append(f"  - {warning}")
            lines.append("")

        lines.extend([
            "Next steps:",
            "-" * 40,
            "  1. Review generated spec.yaml",
            "  2. Fill in all TODO markers",
            "  3. Define decision_rules based on your skill logic",
            "  4. Run: skillspec validate <name> --strict",
            "  5. Run: skillspec generate <name> --force",
            "",
        ])

        return "\n".join(lines)


def migrate_skill(skill_md_path: Path) -> MigrationResult:
    """
    Convenience function to migrate a SKILL.md file.

    Args:
        skill_md_path: Path to the SKILL.md file.

    Returns:
        MigrationResult with generated spec data.
    """
    migrator = SkillMigrator()
    return migrator.migrate(skill_md_path)
