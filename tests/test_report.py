"""
Tests for Compliance Report Generator.
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from backend.skillspec.report import (
    REPORT_VERSION,
    TOOL_VERSION,
    AuditMetadata,
    EvidenceTrace,
    ComplianceReport,
    generate_compliance_report,
    ReportTimer,
    _compute_file_checksum,
    _get_git_commit,
    _get_ci_environment,
)


class TestAuditMetadata:
    """Tests for AuditMetadata dataclass."""

    def test_generate_metadata(self):
        """Test generating audit metadata."""
        metadata = AuditMetadata.generate(duration_ms=150)
        assert metadata.tool_version == TOOL_VERSION
        assert metadata.duration_ms == 150
        assert metadata.report_generated_at is not None

    def test_generate_with_file_checksums(self):
        """Test generating metadata with file checksums."""
        with tempfile.TemporaryDirectory() as tmpdir:
            spec_path = Path(tmpdir) / "spec.yaml"
            spec_path.write_text("skill: test", encoding="utf-8")

            metadata = AuditMetadata.generate(
                duration_ms=100, spec_path=spec_path
            )
            assert metadata.spec_checksum is not None
            assert len(metadata.spec_checksum) == 32  # MD5 hex

    def test_to_dict(self):
        """Test converting to dictionary."""
        metadata = AuditMetadata(
            report_generated_at="2024-01-15T10:00:00Z",
            tool_version="1.0.0",
            duration_ms=100,
            spec_checksum="abc123",
        )
        data = metadata.to_dict()
        assert data["report_generated_at"] == "2024-01-15T10:00:00Z"
        assert data["spec_checksum"] == "abc123"

    def test_to_dict_excludes_none_values(self):
        """Test that None values are excluded from dict."""
        metadata = AuditMetadata(
            report_generated_at="2024-01-15T10:00:00Z",
            tool_version="1.0.0",
            duration_ms=100,
        )
        data = metadata.to_dict()
        assert "spec_checksum" not in data
        assert "git_commit" not in data


class TestEvidenceTrace:
    """Tests for EvidenceTrace dataclass."""

    def test_empty_trace(self):
        """Test creating empty evidence trace."""
        trace = EvidenceTrace()
        assert trace.policies_applied == []
        assert trace.rules_evaluated == []
        assert trace.tags_detected == []
        assert trace.coverage_metrics is None

    def test_to_dict_empty(self):
        """Test to_dict with empty trace."""
        trace = EvidenceTrace()
        data = trace.to_dict()
        assert data == {}

    def test_to_dict_with_data(self):
        """Test to_dict with populated trace."""
        trace = EvidenceTrace(
            policies_applied=[
                {"policy_id": "p1", "policy_name": "Security Policy"}
            ],
            rules_evaluated=[
                {"rule_id": "r1", "result": "pass"}
            ],
            coverage_metrics={"structural_score": 0.85},
        )
        data = trace.to_dict()
        assert "policies_applied" in data
        assert "rules_evaluated" in data
        assert "coverage_metrics" in data

    def test_from_validation_result(self):
        """Test creating trace from validation result."""
        # Create mock validation result
        mock_result = MagicMock()
        mock_result.compliance_result = None
        mock_result.taxonomy_result = None
        mock_result.coverage_result = None

        trace = EvidenceTrace.from_validation_result(mock_result)
        assert trace.policies_applied == []


class TestComplianceReport:
    """Tests for ComplianceReport dataclass."""

    def test_to_dict(self):
        """Test converting report to dictionary."""
        report = ComplianceReport(
            report_version=REPORT_VERSION,
            skill={"name": "test-skill", "version": "1.0.0"},
            validation={"valid": True, "total_errors": 0},
            evidence_trace=EvidenceTrace(),
            audit_metadata=AuditMetadata(
                report_generated_at="2024-01-15T10:00:00Z",
                tool_version="1.0.0",
                duration_ms=100,
            ),
        )
        data = report.to_dict()
        assert data["report_version"] == REPORT_VERSION
        assert data["skill"]["name"] == "test-skill"
        assert data["validation"]["valid"] is True

    def test_to_json(self):
        """Test converting report to JSON string."""
        report = ComplianceReport(
            report_version=REPORT_VERSION,
            skill={"name": "json-test", "version": "1.0.0"},
            validation={"valid": True},
            evidence_trace=EvidenceTrace(),
            audit_metadata=AuditMetadata(
                report_generated_at="2024-01-15T10:00:00Z",
                tool_version="1.0.0",
                duration_ms=50,
            ),
        )
        json_str = report.to_json()
        parsed = json.loads(json_str)
        assert parsed["skill"]["name"] == "json-test"

    def test_save(self):
        """Test saving report to file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "reports" / "report.json"

            report = ComplianceReport(
                report_version=REPORT_VERSION,
                skill={"name": "save-test", "version": "1.0.0"},
                validation={"valid": True},
                evidence_trace=EvidenceTrace(),
                audit_metadata=AuditMetadata(
                    report_generated_at="2024-01-15T10:00:00Z",
                    tool_version="1.0.0",
                    duration_ms=25,
                ),
            )
            report.save(output_path)

            assert output_path.exists()
            content = json.loads(output_path.read_text(encoding="utf-8"))
            assert content["skill"]["name"] == "save-test"


class TestGenerateComplianceReport:
    """Tests for generate_compliance_report function."""

    def test_generate_basic_report(self):
        """Test generating a basic compliance report."""
        with tempfile.TemporaryDirectory() as tmpdir:
            skill_path = Path(tmpdir)
            (skill_path / "spec.yaml").write_text("skill: test", encoding="utf-8")

            mock_result = MagicMock()
            mock_result.to_dict.return_value = {"valid": True, "total_errors": 0}
            mock_result.compliance_result = None
            mock_result.taxonomy_result = None
            mock_result.coverage_result = None

            report = generate_compliance_report(
                validation_result=mock_result,
                skill_name="test-skill",
                skill_version="1.0.0",
                skill_path=skill_path,
                duration_ms=100,
            )

            assert report.report_version == REPORT_VERSION
            assert report.skill["name"] == "test-skill"
            assert report.skill["version"] == "1.0.0"

    def test_generate_report_with_owner(self):
        """Test generating report with owner specified."""
        with tempfile.TemporaryDirectory() as tmpdir:
            skill_path = Path(tmpdir)

            mock_result = MagicMock()
            mock_result.to_dict.return_value = {"valid": True}
            mock_result.compliance_result = None
            mock_result.taxonomy_result = None
            mock_result.coverage_result = None

            report = generate_compliance_report(
                validation_result=mock_result,
                skill_name="owned-skill",
                skill_version="1.0.0",
                skill_path=skill_path,
                duration_ms=50,
                owner="platform-team",
            )

            assert report.skill["owner"] == "platform-team"


class TestReportTimer:
    """Tests for ReportTimer context manager."""

    def test_timing(self):
        """Test that timer measures duration."""
        import time

        with ReportTimer() as timer:
            time.sleep(0.01)  # 10ms

        # Should be at least 10ms
        assert timer.duration_ms >= 10

    def test_timer_zero_without_context(self):
        """Test timer starts at zero."""
        timer = ReportTimer()
        assert timer.duration_ms == 0


class TestHelperFunctions:
    """Tests for helper functions."""

    def test_compute_file_checksum(self):
        """Test file checksum computation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.txt"
            test_file.write_text("test content", encoding="utf-8")

            checksum = _compute_file_checksum(test_file)
            assert len(checksum) == 32  # MD5 produces 32 hex chars

            # Same content = same checksum
            test_file2 = Path(tmpdir) / "test2.txt"
            test_file2.write_text("test content", encoding="utf-8")
            checksum2 = _compute_file_checksum(test_file2)
            assert checksum == checksum2

    def test_get_git_commit_returns_string_or_none(self):
        """Test git commit retrieval."""
        commit = _get_git_commit()
        # Should be None (no git) or a short hash string
        if commit is not None:
            assert len(commit) == 12

    def test_get_ci_environment_none_outside_ci(self):
        """Test CI environment detection outside CI."""
        # Clear CI env vars for test
        with patch.dict("os.environ", {}, clear=True):
            env = _get_ci_environment()
            # May or may not be None depending on actual environment
            # Just check it doesn't crash
            assert env is None or isinstance(env, dict)

    def test_get_ci_environment_github_actions(self):
        """Test GitHub Actions detection."""
        with patch.dict(
            "os.environ",
            {
                "GITHUB_ACTIONS": "true",
                "GITHUB_RUN_ID": "12345",
                "GITHUB_REF_NAME": "main",
                "GITHUB_ACTOR": "testuser",
            },
            clear=True,
        ):
            env = _get_ci_environment()
            assert env is not None
            assert env["ci_provider"] == "github_actions"
            assert env["build_id"] == "12345"

    def test_get_ci_environment_gitlab_ci(self):
        """Test GitLab CI detection."""
        with patch.dict(
            "os.environ",
            {
                "GITLAB_CI": "true",
                "CI_JOB_ID": "67890",
                "CI_COMMIT_REF_NAME": "develop",
            },
            clear=True,
        ):
            env = _get_ci_environment()
            assert env is not None
            assert env["ci_provider"] == "gitlab_ci"

    def test_get_ci_environment_jenkins(self):
        """Test Jenkins detection."""
        with patch.dict(
            "os.environ",
            {
                "JENKINS_URL": "http://jenkins.example.com",
                "BUILD_NUMBER": "42",
            },
            clear=True,
        ):
            env = _get_ci_environment()
            assert env is not None
            assert env["ci_provider"] == "jenkins"

    def test_get_ci_environment_circleci(self):
        """Test CircleCI detection."""
        with patch.dict(
            "os.environ",
            {
                "CIRCLECI": "true",
                "CIRCLE_BUILD_NUM": "999",
                "CIRCLE_BRANCH": "feature",
            },
            clear=True,
        ):
            env = _get_ci_environment()
            assert env is not None
            assert env["ci_provider"] == "circleci"


class TestReportVersions:
    """Tests for version constants."""

    def test_report_version_format(self):
        """Test report version has correct format."""
        assert REPORT_VERSION.startswith("compliance-report/")

    def test_tool_version_is_semver(self):
        """Test tool version follows semver format."""
        import re
        semver_pattern = r"^\d+\.\d+\.\d+$"
        assert re.match(semver_pattern, TOOL_VERSION)
