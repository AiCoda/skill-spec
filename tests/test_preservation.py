"""
Tests for SKILL.md Preservation Protocol.
"""

import pytest

from backend.skillspec.preservation import (
    BlockType,
    ContentBlock,
    ParsedDocument,
    PreservationResult,
    parse_skill_md,
    wrap_generated_block,
    wrap_manual_block,
    merge_with_preservation,
    extract_manual_blocks,
    extract_generated_blocks,
    validate_generated_block_consistency,
    validate_document_consistency,
    add_preservation_markers,
    insert_manual_section,
    GENERATED_START,
    GENERATED_END,
    MANUAL_START,
    MANUAL_END,
)


class TestBlockMarkers:
    """Tests for block marker constants."""

    def test_marker_format(self):
        """Test marker format is correct."""
        assert "skillspec:generated:start" in GENERATED_START
        assert "skillspec:generated:end" in GENERATED_END
        assert "skillspec:manual:start" in MANUAL_START
        assert "skillspec:manual:end" in MANUAL_END


class TestContentBlock:
    """Tests for ContentBlock dataclass."""

    def test_compute_checksum(self):
        """Test checksum computation."""
        block = ContentBlock(block_type=BlockType.GENERATED, content="test content")
        checksum = block.compute_checksum()
        assert len(checksum) == 8
        # Same content should produce same checksum
        block2 = ContentBlock(block_type=BlockType.GENERATED, content="test content")
        assert block.compute_checksum() == block2.compute_checksum()

    def test_different_content_different_checksum(self):
        """Test different content produces different checksum."""
        block1 = ContentBlock(block_type=BlockType.GENERATED, content="content 1")
        block2 = ContentBlock(block_type=BlockType.GENERATED, content="content 2")
        assert block1.compute_checksum() != block2.compute_checksum()


class TestParsedDocument:
    """Tests for ParsedDocument dataclass."""

    def test_get_manual_blocks(self):
        """Test filtering manual blocks."""
        doc = ParsedDocument(
            blocks=[
                ContentBlock(block_type=BlockType.GENERATED, content="gen"),
                ContentBlock(block_type=BlockType.MANUAL, content="manual1"),
                ContentBlock(block_type=BlockType.MANUAL, content="manual2"),
            ]
        )
        manual = doc.get_manual_blocks()
        assert len(manual) == 2
        assert all(b.block_type == BlockType.MANUAL for b in manual)

    def test_get_generated_blocks(self):
        """Test filtering generated blocks."""
        doc = ParsedDocument(
            blocks=[
                ContentBlock(block_type=BlockType.GENERATED, content="gen1"),
                ContentBlock(block_type=BlockType.GENERATED, content="gen2"),
                ContentBlock(block_type=BlockType.MANUAL, content="manual"),
            ]
        )
        generated = doc.get_generated_blocks()
        assert len(generated) == 2

    def test_get_manual_block_by_section(self):
        """Test getting manual block by section name."""
        doc = ParsedDocument(
            blocks=[
                ContentBlock(
                    block_type=BlockType.MANUAL,
                    content="notes",
                    section_name="Custom Notes",
                ),
                ContentBlock(
                    block_type=BlockType.MANUAL,
                    content="refs",
                    section_name="References",
                ),
            ]
        )
        block = doc.get_manual_block_by_section("Custom Notes")
        assert block is not None
        assert block.content == "notes"

        # Non-existent section
        block = doc.get_manual_block_by_section("Unknown")
        assert block is None


class TestParseSkillMd:
    """Tests for parse_skill_md function."""

    def test_parse_unmarked_content(self):
        """Test parsing content without markers."""
        content = """# Skill Name

Some description here.

## Purpose

The purpose of this skill.
"""
        doc = parse_skill_md(content)
        assert doc.has_markers is False
        assert len(doc.blocks) == 1
        assert doc.blocks[0].block_type == BlockType.UNMARKED

    def test_parse_generated_block(self):
        """Test parsing content with generated block."""
        content = f"""# Skill Name

{GENERATED_START}
Generated content here.
{GENERATED_END}
"""
        doc = parse_skill_md(content)
        assert doc.has_markers is True
        generated = doc.get_generated_blocks()
        assert len(generated) == 1
        assert "Generated content" in generated[0].content

    def test_parse_manual_block(self):
        """Test parsing content with manual block."""
        content = f"""# Skill Name

{MANUAL_START}
Manual content that should be preserved.
{MANUAL_END}
"""
        doc = parse_skill_md(content)
        assert doc.has_markers is True
        manual = doc.get_manual_blocks()
        assert len(manual) == 1
        assert "Manual content" in manual[0].content

    def test_parse_mixed_blocks(self):
        """Test parsing content with both generated and manual blocks."""
        content = f"""# Skill

{GENERATED_START}
Auto-generated from spec.yaml
{GENERATED_END}

{MANUAL_START}
Custom notes by user.
{MANUAL_END}
"""
        doc = parse_skill_md(content)
        assert doc.has_markers is True
        assert len(doc.get_generated_blocks()) == 1
        assert len(doc.get_manual_blocks()) == 1


class TestWrapFunctions:
    """Tests for wrap_generated_block and wrap_manual_block."""

    def test_wrap_generated_block(self):
        """Test wrapping content in generated markers."""
        content = "Some generated content"
        wrapped = wrap_generated_block(content)
        assert GENERATED_START in wrapped
        assert GENERATED_END in wrapped
        assert content in wrapped

    def test_wrap_manual_block(self):
        """Test wrapping content in manual markers."""
        content = "Some manual content"
        wrapped = wrap_manual_block(content)
        assert MANUAL_START in wrapped
        assert MANUAL_END in wrapped
        assert content in wrapped


class TestMergeWithPreservation:
    """Tests for merge_with_preservation function."""

    def test_force_mode_replaces_all(self):
        """Test force mode replaces everything."""
        existing = f"""# Old

{MANUAL_START}
Important manual notes.
{MANUAL_END}
"""
        new_content = "# New\n\nCompletely new content."
        result = merge_with_preservation(existing, new_content, force=True)

        assert result.success is True
        assert result.merged_content == new_content
        assert "Important manual" not in result.merged_content
        assert len(result.warnings) > 0

    def test_preserve_manual_blocks(self):
        """Test that manual blocks are preserved."""
        existing = f"""# Skill

{GENERATED_START}
Old generated content
{GENERATED_END}

{MANUAL_START}
User's custom notes - DO NOT DELETE.
{MANUAL_END}
"""
        new_content = "# Skill\n\nNew generated content here."
        result = merge_with_preservation(existing, new_content)

        assert result.success is True
        assert "custom notes" in result.merged_content
        assert result.manual_blocks_preserved == 1
        assert result.generated_blocks_updated == 1

    def test_unmarked_content_gets_wrapped(self):
        """Test that unmarked existing content gets wrapped."""
        existing = "# Plain Skill\n\nNo markers here."
        new_content = "# New Skill\n\nNew content."

        result = merge_with_preservation(existing, new_content)
        assert result.success is True
        assert GENERATED_START in result.merged_content


class TestExtractFunctions:
    """Tests for extract_manual_blocks and extract_generated_blocks."""

    def test_extract_manual_blocks(self):
        """Test extracting manual blocks."""
        content = f"""# Skill

{MANUAL_START}
First manual block.
{MANUAL_END}

Some text.

{MANUAL_START}
Second manual block.
{MANUAL_END}
"""
        blocks = extract_manual_blocks(content)
        assert len(blocks) == 2

    def test_extract_generated_blocks(self):
        """Test extracting generated blocks."""
        content = f"""# Skill

{GENERATED_START}
Generated from spec.
{GENERATED_END}
"""
        blocks = extract_generated_blocks(content)
        assert len(blocks) == 1


class TestValidateConsistency:
    """Tests for consistency validation functions."""

    def test_validate_generated_block_consistency_same_content(self):
        """Test consistency when content matches."""
        block = ContentBlock(
            block_type=BlockType.GENERATED,
            content="Same content here",
        )
        is_consistent, diff = validate_generated_block_consistency(
            block, "Same content here"
        )
        assert is_consistent is True
        assert diff is None

    def test_validate_generated_block_consistency_different_content(self):
        """Test consistency when content differs."""
        block = ContentBlock(
            block_type=BlockType.GENERATED,
            content="Old content",
        )
        is_consistent, diff = validate_generated_block_consistency(
            block, "New content"
        )
        assert is_consistent is False
        assert diff is not None

    def test_validate_document_consistency_no_generated(self):
        """Test document consistency when no generated blocks."""
        content = f"""# Skill

{MANUAL_START}
Only manual content.
{MANUAL_END}
"""
        result = validate_document_consistency(content, "Any spec content")
        assert result.valid is True
        assert result.blocks_checked == 0

    def test_validate_document_consistency_with_mismatch(self):
        """Test document consistency with mismatched generated block."""
        content = f"""# Skill

{GENERATED_START}
Old generated content.
{GENERATED_END}
"""
        result = validate_document_consistency(content, "New generated content.")
        assert result.valid is False
        assert len(result.inconsistencies) > 0


class TestAddPreservationMarkers:
    """Tests for add_preservation_markers function."""

    def test_add_markers_to_unmarked(self):
        """Test adding markers to unmarked content."""
        content = "# Skill\n\nPlain content."
        result = add_preservation_markers(content)
        assert GENERATED_START in result
        assert GENERATED_END in result

    def test_keep_existing_markers(self):
        """Test that existing markers are not duplicated."""
        content = f"""# Skill

{GENERATED_START}
Already marked.
{GENERATED_END}
"""
        result = add_preservation_markers(content)
        # Should return unchanged
        assert result == content


class TestInsertManualSection:
    """Tests for insert_manual_section function."""

    def test_insert_at_end(self):
        """Test inserting manual section at end."""
        content = "# Skill\n\n## Purpose\n\nThe purpose."
        manual = "Custom notes here."
        result = insert_manual_section(content, manual)

        assert MANUAL_START in result
        assert MANUAL_END in result
        assert "Custom notes" in result

    def test_insert_after_section(self):
        """Test inserting manual section after specific section."""
        content = """# Skill

## Purpose

The purpose.

## Decision Rules

Some rules.
"""
        manual = "Notes about the purpose."
        result = insert_manual_section(content, manual, after_section="Purpose")

        assert MANUAL_START in result
        # Manual block should appear before Decision Rules
        purpose_idx = result.find("## Purpose")
        manual_idx = result.find(MANUAL_START)
        rules_idx = result.find("## Decision Rules")
        assert purpose_idx < manual_idx < rules_idx
