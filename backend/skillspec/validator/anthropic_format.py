"""
Anthropic Format Validator

Validates SKILL.md files against Anthropic's official skill format requirements.

Format Requirements:
1. Frontmatter (required): name, description
2. Required Sections: Description, Instructions, Limitations
3. Recommended Sections: When to Use, Examples, Edge Cases, Error Codes, Related Skills
"""

import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Optional


class SectionRequirement(Enum):
    """Section requirement level."""
    REQUIRED = "required"
    RECOMMENDED = "recommended"
    OPTIONAL = "optional"


@dataclass
class FrontmatterValidation:
    """Result of frontmatter validation."""
    valid: bool
    name: Optional[str] = None
    description: Optional[str] = None
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


@dataclass
class SectionValidation:
    """Result of section validation."""
    name: str
    requirement: SectionRequirement
    present: bool
    line_number: Optional[int] = None
    content_length: int = 0
    has_content: bool = False
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


@dataclass
class ExampleValidation:
    """Result of example validation."""
    name: str
    has_input: bool = False
    has_output: bool = False
    line_number: int = 0
    errors: list[str] = field(default_factory=list)


@dataclass
class AnthropicFormatResult:
    """Complete format validation result."""
    valid: bool
    skill_name: str
    file_path: str
    frontmatter: FrontmatterValidation
    sections: list[SectionValidation] = field(default_factory=list)
    examples: list[ExampleValidation] = field(default_factory=list)
    total_errors: int = 0
    total_warnings: int = 0
    compliance_score: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON output."""
        return {
            "valid": self.valid,
            "skill_name": self.skill_name,
            "file_path": self.file_path,
            "frontmatter": {
                "valid": self.frontmatter.valid,
                "name": self.frontmatter.name,
                "description": self.frontmatter.description,
                "errors": self.frontmatter.errors,
                "warnings": self.frontmatter.warnings,
            },
            "sections": [
                {
                    "name": s.name,
                    "requirement": s.requirement.value,
                    "present": s.present,
                    "has_content": s.has_content,
                    "errors": s.errors,
                    "warnings": s.warnings,
                }
                for s in self.sections
            ],
            "examples": [
                {
                    "name": e.name,
                    "has_input": e.has_input,
                    "has_output": e.has_output,
                    "errors": e.errors,
                }
                for e in self.examples
            ],
            "total_errors": self.total_errors,
            "total_warnings": self.total_warnings,
            "compliance_score": self.compliance_score,
        }

    def summary(self) -> str:
        """Generate human-readable summary."""
        lines = []
        status = "PASSED" if self.valid else "FAILED"
        lines.append(f"Anthropic Format Check: {status}")
        lines.append(f"  Skill: {self.skill_name}")
        lines.append(f"  File: {self.file_path}")
        lines.append(f"  Compliance Score: {self.compliance_score:.0%}")
        lines.append(f"  Errors: {self.total_errors}, Warnings: {self.total_warnings}")

        if self.frontmatter.errors:
            lines.append("\n  Frontmatter Errors:")
            for err in self.frontmatter.errors:
                lines.append(f"    - {err}")

        missing_required = [s for s in self.sections
                           if s.requirement == SectionRequirement.REQUIRED and not s.present]
        if missing_required:
            lines.append("\n  Missing Required Sections:")
            for s in missing_required:
                lines.append(f"    - {s.name}")

        missing_recommended = [s for s in self.sections
                              if s.requirement == SectionRequirement.RECOMMENDED and not s.present]
        if missing_recommended:
            lines.append("\n  Missing Recommended Sections:")
            for s in missing_recommended:
                lines.append(f"    - {s.name}")

        return "\n".join(lines)


# Section definitions with requirements
SECTION_DEFINITIONS = {
    "Description": SectionRequirement.REQUIRED,
    "Instructions": SectionRequirement.REQUIRED,
    "Limitations": SectionRequirement.REQUIRED,
    "When to Use": SectionRequirement.RECOMMENDED,
    "Examples": SectionRequirement.RECOMMENDED,
    "Edge Cases": SectionRequirement.RECOMMENDED,
    "Error Codes": SectionRequirement.RECOMMENDED,
    "Related Skills": SectionRequirement.RECOMMENDED,
}

# Alternative section names mapping
# Maps lowercase alternative names to canonical Anthropic section names
SECTION_ALIASES = {
    # Description alternatives
    "purpose": "Description",
    "overview": "Description",
    "about": "Description",
    # Instructions alternatives
    "workflow": "Instructions",
    "steps": "Instructions",
    "how it works": "Instructions",
    "usage": "Instructions",
    "how to use": "When to Use",
    "use cases": "When to Use",
    # Limitations alternatives
    "what this skill does not do": "Limitations",
    "non-goals": "Limitations",
    "non goals": "Limitations",
    "exclusions": "Limitations",
    "out of scope": "Limitations",
    # When to Use alternatives
    "triggers": "When to Use",
    "when to use this": "When to Use",
    "activation": "When to Use",
    # Examples alternatives
    "example": "Examples",
    "sample": "Examples",
    "samples": "Examples",
    # Edge Cases alternatives
    "edge case": "Edge Cases",
    "boundary conditions": "Edge Cases",
    "special cases": "Edge Cases",
    # Error Codes alternatives
    "errors": "Error Codes",
    "error handling": "Error Codes",
    "failure modes": "Error Codes",
    # Related Skills alternatives
    "related": "Related Skills",
    "see also": "Related Skills",
    "works well with": "Related Skills",
}


class AnthropicFormatValidator:
    """
    Validator for Anthropic SKILL.md format compliance.

    Validates:
    1. Frontmatter presence and required fields (name, description)
    2. Required sections (Description, Instructions, Limitations)
    3. Recommended sections (When to Use, Examples, Edge Cases, etc.)
    4. Example format (Input/Output structure)
    """

    def __init__(self) -> None:
        """Initialize validator."""
        self.section_definitions = SECTION_DEFINITIONS.copy()
        self.section_aliases = SECTION_ALIASES.copy()

    def validate_file(self, file_path: str | Path) -> AnthropicFormatResult:
        """
        Validate a SKILL.md file.

        Args:
            file_path: Path to the SKILL.md file

        Returns:
            AnthropicFormatResult with validation details
        """
        file_path = Path(file_path)

        if not file_path.exists():
            return AnthropicFormatResult(
                valid=False,
                skill_name="unknown",
                file_path=str(file_path),
                frontmatter=FrontmatterValidation(
                    valid=False,
                    errors=[f"File not found: {file_path}"]
                ),
                total_errors=1,
            )

        content = file_path.read_text(encoding="utf-8")
        return self.validate_content(content, str(file_path))

    def validate_content(self, content: str, file_path: str = "SKILL.md") -> AnthropicFormatResult:
        """
        Validate SKILL.md content.

        Args:
            content: Markdown content to validate
            file_path: File path for reporting

        Returns:
            AnthropicFormatResult with validation details
        """
        # Parse frontmatter
        frontmatter = self._validate_frontmatter(content)

        # Parse and validate sections
        sections = self._validate_sections(content)

        # Validate examples if present
        examples = self._validate_examples(content)

        # Calculate totals
        total_errors = len(frontmatter.errors)
        total_warnings = len(frontmatter.warnings)

        for section in sections:
            total_errors += len(section.errors)
            total_warnings += len(section.warnings)

        for example in examples:
            total_errors += len(example.errors)

        # Calculate compliance score
        compliance_score = self._calculate_compliance_score(frontmatter, sections)

        # Overall validity
        valid = (
            frontmatter.valid
            and all(s.present for s in sections if s.requirement == SectionRequirement.REQUIRED)
        )

        skill_name = frontmatter.name or "unknown"

        return AnthropicFormatResult(
            valid=valid,
            skill_name=skill_name,
            file_path=file_path,
            frontmatter=frontmatter,
            sections=sections,
            examples=examples,
            total_errors=total_errors,
            total_warnings=total_warnings,
            compliance_score=compliance_score,
        )

    def _validate_frontmatter(self, content: str) -> FrontmatterValidation:
        """Validate frontmatter section."""
        errors = []
        warnings = []
        name = None
        description = None

        # Check for frontmatter
        frontmatter_pattern = r'^---\s*\n(.*?)\n---'
        match = re.match(frontmatter_pattern, content, re.DOTALL)

        if not match:
            errors.append("Missing frontmatter block (--- ... ---)")
            return FrontmatterValidation(valid=False, errors=errors)

        frontmatter_content = match.group(1)

        # Extract name
        name_match = re.search(r'^name:\s*["\']?([^"\'\n]+)["\']?\s*$',
                               frontmatter_content, re.MULTILINE)
        if name_match:
            name = name_match.group(1).strip()
        else:
            errors.append("Missing required field: name")

        # Extract description
        desc_match = re.search(r'^description:\s*["\']?([^"\n]+(?:\n(?![a-z]+:)[^"\n]+)*)["\']?\s*$',
                               frontmatter_content, re.MULTILINE)
        if desc_match:
            description = desc_match.group(1).strip().strip('"\'')
        else:
            errors.append("Missing required field: description")

        # Validate description length
        if description:
            if len(description) < 20:
                warnings.append("Description is very short (< 20 chars)")
            elif len(description) > 300:
                warnings.append("Description is very long (> 300 chars)")

        valid = len(errors) == 0
        return FrontmatterValidation(
            valid=valid,
            name=name,
            description=description,
            errors=errors,
            warnings=warnings,
        )

    def _validate_sections(self, content: str) -> list[SectionValidation]:
        """Validate required and recommended sections."""
        results = []

        # Find all h2 sections (## Section Name)
        section_pattern = r'^##\s+(.+?)$'
        sections_found: dict[str, tuple[int, str]] = {}

        lines = content.split('\n')
        current_section = None
        current_content: list[str] = []

        for i, line in enumerate(lines, 1):
            match = re.match(section_pattern, line)
            if match:
                # Save previous section content
                if current_section:
                    sections_found[current_section] = (
                        sections_found.get(current_section, (0, ""))[0],
                        '\n'.join(current_content)
                    )

                section_name = match.group(1).strip()
                # Normalize section name
                normalized = self._normalize_section_name(section_name)
                if normalized:
                    sections_found[normalized] = (i, "")
                    current_section = normalized
                    current_content = []
                else:
                    current_section = section_name
                    current_content = []
            elif current_section:
                current_content.append(line)

        # Save last section content
        if current_section and current_section in sections_found:
            sections_found[current_section] = (
                sections_found[current_section][0],
                '\n'.join(current_content)
            )

        # Validate each expected section
        for section_name, requirement in self.section_definitions.items():
            present = section_name in sections_found
            line_number = None
            content_text = ""
            has_content = False

            if present:
                line_number, content_text = sections_found[section_name]
                has_content = len(content_text.strip()) > 10

            errors = []
            warnings = []

            if requirement == SectionRequirement.REQUIRED and not present:
                errors.append(f"Missing required section: {section_name}")
            elif requirement == SectionRequirement.RECOMMENDED and not present:
                warnings.append(f"Missing recommended section: {section_name}")
            elif present and not has_content:
                warnings.append(f"Section '{section_name}' appears empty or minimal")

            results.append(SectionValidation(
                name=section_name,
                requirement=requirement,
                present=present,
                line_number=line_number,
                content_length=len(content_text),
                has_content=has_content,
                errors=errors,
                warnings=warnings,
            ))

        return results

    def _normalize_section_name(self, name: str) -> Optional[str]:
        """Normalize section name to canonical form."""
        name_lower = name.lower().strip()

        # Direct match
        for canonical in self.section_definitions:
            if canonical.lower() == name_lower:
                return canonical

        # Alias match
        if name_lower in self.section_aliases:
            return self.section_aliases[name_lower]

        # Partial match
        for canonical in self.section_definitions:
            if name_lower in canonical.lower() or canonical.lower() in name_lower:
                return canonical

        return None

    def _validate_examples(self, content: str) -> list[ExampleValidation]:
        """Validate Examples section format."""
        results = []

        # Find Examples section
        examples_match = re.search(r'^##\s+Examples?\s*$(.*?)(?=^##\s|\Z)',
                                   content, re.MULTILINE | re.DOTALL)
        if not examples_match:
            return results

        examples_content = examples_match.group(1)

        # Find individual examples (### Example N: Name)
        example_pattern = r'^###\s+Example\s*\d*:?\s*(.+?)$'
        example_matches = list(re.finditer(example_pattern, examples_content, re.MULTILINE))

        for i, match in enumerate(example_matches):
            example_name = match.group(1).strip()
            start = match.end()
            end = example_matches[i + 1].start() if i + 1 < len(example_matches) else len(examples_content)
            example_text = examples_content[start:end]

            # Check for Input/Output
            has_input = bool(re.search(r'\*\*Input[:\*]|```.*\n.*source_|Input:', example_text, re.IGNORECASE))
            has_output = bool(re.search(r'\*\*Output[:\*]|```.*\n.*"status"|Output:', example_text, re.IGNORECASE))

            errors = []
            if not has_input:
                errors.append(f"Example '{example_name}' missing Input section")
            if not has_output:
                errors.append(f"Example '{example_name}' missing Output section")

            results.append(ExampleValidation(
                name=example_name,
                has_input=has_input,
                has_output=has_output,
                line_number=0,
                errors=errors,
            ))

        return results

    def _calculate_compliance_score(
        self,
        frontmatter: FrontmatterValidation,
        sections: list[SectionValidation]
    ) -> float:
        """Calculate overall compliance score (0.0 to 1.0)."""
        total_points = 0.0
        earned_points = 0.0

        # Frontmatter: 20 points
        total_points += 20
        if frontmatter.valid:
            earned_points += 20
        elif frontmatter.name:
            earned_points += 10
        elif frontmatter.description:
            earned_points += 10

        # Required sections: 15 points each (45 total)
        required_sections = [s for s in sections if s.requirement == SectionRequirement.REQUIRED]
        for section in required_sections:
            total_points += 15
            if section.present:
                earned_points += 10
                if section.has_content:
                    earned_points += 5

        # Recommended sections: 7 points each (35 total for 5 sections)
        recommended_sections = [s for s in sections if s.requirement == SectionRequirement.RECOMMENDED]
        for section in recommended_sections:
            total_points += 7
            if section.present:
                earned_points += 5
                if section.has_content:
                    earned_points += 2

        return earned_points / total_points if total_points > 0 else 0.0

    def extract_when_to_use_from_spec(self, spec: dict[str, Any]) -> list[str]:
        """
        Auto-generate "When to Use" content from spec decision_rules.

        Args:
            spec: Parsed spec.yaml content

        Returns:
            List of "When to Use" trigger descriptions
        """
        triggers = []

        # Extract from decision_rules
        decision_rules = spec.get("decision_rules", [])
        if isinstance(decision_rules, list):
            for rule in decision_rules:
                if isinstance(rule, dict):
                    when = rule.get("when", "")
                    then = rule.get("then", {})
                    if isinstance(then, dict) and then.get("status") == "success":
                        # Convert condition to human-readable trigger
                        trigger = self._condition_to_trigger(when)
                        if trigger:
                            triggers.append(trigger)

        # Extract from context.scenarios
        context = spec.get("context", {})
        scenarios = context.get("scenarios", [])
        for scenario in scenarios:
            if isinstance(scenario, dict):
                trigger = scenario.get("trigger", "")
                if trigger:
                    triggers.append(trigger)

        return triggers

    def _condition_to_trigger(self, condition: str) -> Optional[str]:
        """Convert a rule condition to human-readable trigger."""
        if not condition or condition == "true":
            return None

        # Simple transformations
        condition = condition.replace("==", "is")
        condition = condition.replace("!=", "is not")
        condition = condition.replace("contains(", "contains ")
        condition = condition.replace(")", "")
        condition = condition.replace("_", " ")

        return f"When {condition}"


def validate_skill_md(file_path: str | Path) -> AnthropicFormatResult:
    """
    Convenience function to validate a SKILL.md file.

    Args:
        file_path: Path to the SKILL.md file

    Returns:
        AnthropicFormatResult with validation details
    """
    validator = AnthropicFormatValidator()
    return validator.validate_file(file_path)
