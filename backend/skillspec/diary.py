"""
Diary System for Skill Evidence Tracking.

This module provides functionality for logging and managing execution evidence
for skills, supporting audit trails and quality tracking.
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional
from uuid import uuid4


@dataclass
class DiaryEvent:
    """
    A single diary event recording skill execution or test run.

    Attributes:
        event_id: Unique identifier for this event.
        event_type: Type of event (test_run, production_execution, validation).
        skill_name: Name of the skill.
        timestamp: ISO format timestamp.
        duration_ms: Duration in milliseconds.
        success: Whether the execution succeeded.
        inputs: Input data (may be redacted for production).
        outputs: Output data (may be redacted for production).
        error: Error message if failed.
        trace_file: Path to detailed trace file if available.
        metadata: Additional metadata (environment, version, etc.).
    """

    event_id: str
    event_type: str
    skill_name: str
    timestamp: str
    duration_ms: int
    success: bool
    inputs: Optional[Dict[str, Any]] = None
    outputs: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    trace_file: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def create(
        cls,
        event_type: str,
        skill_name: str,
        duration_ms: int,
        success: bool,
        inputs: Optional[Dict[str, Any]] = None,
        outputs: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
        trace_file: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> "DiaryEvent":
        """Create a new diary event with auto-generated ID and timestamp."""
        return cls(
            event_id=str(uuid4()),
            event_type=event_type,
            skill_name=skill_name,
            timestamp=datetime.utcnow().isoformat() + "Z",
            duration_ms=duration_ms,
            success=success,
            inputs=inputs,
            outputs=outputs,
            error=error,
            trace_file=trace_file,
            metadata=metadata or {},
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DiaryEvent":
        """Create from dictionary."""
        return cls(**data)

    def to_json(self) -> str:
        """Serialize to JSON string."""
        return json.dumps(self.to_dict())

    @classmethod
    def from_json(cls, json_str: str) -> "DiaryEvent":
        """Deserialize from JSON string."""
        return cls.from_dict(json.loads(json_str))


@dataclass
class DiarySummary:
    """
    Summary statistics for a skill's diary.

    Attributes:
        skill_name: Name of the skill.
        total_events: Total number of events.
        test_runs: Number of test runs.
        production_runs: Number of production executions.
        success_rate: Success rate as percentage (0-100).
        avg_duration_ms: Average duration in milliseconds.
        last_test_run: Timestamp of last test run.
        last_production_run: Timestamp of last production run.
        error_counts: Count of errors by error message.
    """

    skill_name: str
    total_events: int
    test_runs: int
    production_runs: int
    success_rate: float
    avg_duration_ms: float
    last_test_run: Optional[str]
    last_production_run: Optional[str]
    error_counts: Dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)

    def format_report(self) -> str:
        """Format as human-readable report."""
        lines = [
            f"Diary Summary: {self.skill_name}",
            f"  Total Events: {self.total_events}",
            f"  Test Runs: {self.test_runs}",
            f"  Production Runs: {self.production_runs}",
            f"  Success Rate: {self.success_rate:.1f}%",
            f"  Average Duration: {self.avg_duration_ms:.0f}ms",
        ]
        if self.last_test_run:
            lines.append(f"  Last Test Run: {self.last_test_run}")
        if self.last_production_run:
            lines.append(f"  Last Production Run: {self.last_production_run}")
        if self.error_counts:
            lines.append("  Error Counts:")
            for error, count in sorted(
                self.error_counts.items(), key=lambda x: -x[1]
            )[:5]:
                lines.append(f"    - {error}: {count}")
        return "\n".join(lines)


class DiaryManager:
    """
    Manages diary events for skills.

    The diary is stored as a JSONL file at .skillspec/diary.jsonl relative
    to the skill directory. Trace files are stored in .skillspec/traces/.
    """

    DIARY_DIR = ".skillspec"
    DIARY_FILE = "diary.jsonl"
    TRACES_DIR = "traces"

    def __init__(self, base_dir: Path):
        """
        Initialize the diary manager.

        Args:
            base_dir: Base directory for skill files (typically skillspec/).
        """
        self.base_dir = Path(base_dir)
        self.diary_dir = self.base_dir / self.DIARY_DIR
        self.diary_file = self.diary_dir / self.DIARY_FILE
        self.traces_dir = self.diary_dir / self.TRACES_DIR

    def ensure_dirs(self) -> None:
        """Ensure diary directories exist."""
        self.diary_dir.mkdir(parents=True, exist_ok=True)
        self.traces_dir.mkdir(parents=True, exist_ok=True)

    def log_event(self, event: DiaryEvent) -> None:
        """
        Log a diary event.

        Args:
            event: The event to log.
        """
        self.ensure_dirs()
        with open(self.diary_file, "a", encoding="utf-8") as f:
            f.write(event.to_json() + "\n")

    def log_test_run(
        self,
        skill_name: str,
        duration_ms: int,
        success: bool,
        inputs: Optional[Dict[str, Any]] = None,
        outputs: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
        trace_data: Optional[Dict[str, Any]] = None,
    ) -> DiaryEvent:
        """
        Log a test run event.

        Args:
            skill_name: Name of the skill.
            duration_ms: Duration in milliseconds.
            success: Whether the test passed.
            inputs: Test inputs.
            outputs: Test outputs.
            error: Error message if failed.
            trace_data: Detailed trace data to store.

        Returns:
            The created diary event.
        """
        trace_file = None
        if trace_data:
            trace_file = self._save_trace(skill_name, "test", trace_data)

        event = DiaryEvent.create(
            event_type="test_run",
            skill_name=skill_name,
            duration_ms=duration_ms,
            success=success,
            inputs=inputs,
            outputs=outputs,
            error=error,
            trace_file=trace_file,
            metadata={"environment": "test"},
        )
        self.log_event(event)
        return event

    def log_production_execution(
        self,
        skill_name: str,
        duration_ms: int,
        success: bool,
        error: Optional[str] = None,
        trace_data: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> DiaryEvent:
        """
        Log a production execution event.

        Note: Inputs/outputs are not stored for production events for privacy.

        Args:
            skill_name: Name of the skill.
            duration_ms: Duration in milliseconds.
            success: Whether execution succeeded.
            error: Error message if failed.
            trace_data: Detailed trace data to store.
            metadata: Additional metadata.

        Returns:
            The created diary event.
        """
        trace_file = None
        if trace_data:
            trace_file = self._save_trace(skill_name, "production", trace_data)

        event_metadata = {"environment": "production"}
        if metadata:
            event_metadata.update(metadata)

        event = DiaryEvent.create(
            event_type="production_execution",
            skill_name=skill_name,
            duration_ms=duration_ms,
            success=success,
            error=error,
            trace_file=trace_file,
            metadata=event_metadata,
        )
        self.log_event(event)
        return event

    def _save_trace(
        self,
        skill_name: str,
        event_type: str,
        trace_data: Dict[str, Any],
    ) -> str:
        """Save trace data to file and return relative path."""
        self.ensure_dirs()
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        trace_id = str(uuid4())[:8]
        filename = f"{skill_name}_{event_type}_{timestamp}_{trace_id}.json"
        trace_path = self.traces_dir / filename

        with open(trace_path, "w", encoding="utf-8") as f:
            json.dump(trace_data, f, indent=2)

        # Return relative path from diary_dir
        return str(Path(self.TRACES_DIR) / filename)

    def read_events(
        self,
        skill_name: Optional[str] = None,
        event_type: Optional[str] = None,
        since: Optional[datetime] = None,
    ) -> Iterator[DiaryEvent]:
        """
        Read diary events with optional filtering.

        Args:
            skill_name: Filter by skill name.
            event_type: Filter by event type.
            since: Filter events after this datetime.

        Yields:
            Matching diary events.
        """
        if not self.diary_file.exists():
            return

        with open(self.diary_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    event = DiaryEvent.from_json(line)
                except (json.JSONDecodeError, TypeError):
                    continue

                # Apply filters
                if skill_name and event.skill_name != skill_name:
                    continue
                if event_type and event.event_type != event_type:
                    continue
                if since:
                    event_time = datetime.fromisoformat(
                        event.timestamp.replace("Z", "+00:00")
                    )
                    if event_time < since.replace(tzinfo=event_time.tzinfo):
                        continue

                yield event

    def get_events_for_skill(self, skill_name: str) -> List[DiaryEvent]:
        """Get all events for a specific skill."""
        return list(self.read_events(skill_name=skill_name))

    def get_summary(self, skill_name: str) -> DiarySummary:
        """
        Generate summary statistics for a skill.

        Args:
            skill_name: Name of the skill.

        Returns:
            Summary statistics.
        """
        events = self.get_events_for_skill(skill_name)

        if not events:
            return DiarySummary(
                skill_name=skill_name,
                total_events=0,
                test_runs=0,
                production_runs=0,
                success_rate=0.0,
                avg_duration_ms=0.0,
                last_test_run=None,
                last_production_run=None,
                error_counts={},
            )

        test_runs = [e for e in events if e.event_type == "test_run"]
        production_runs = [e for e in events if e.event_type == "production_execution"]
        successful = sum(1 for e in events if e.success)

        # Calculate error counts
        error_counts: Dict[str, int] = {}
        for e in events:
            if e.error:
                error_key = e.error[:50]  # Truncate long errors
                error_counts[error_key] = error_counts.get(error_key, 0) + 1

        # Find last runs
        last_test = max(
            (e.timestamp for e in test_runs), default=None
        )
        last_prod = max(
            (e.timestamp for e in production_runs), default=None
        )

        return DiarySummary(
            skill_name=skill_name,
            total_events=len(events),
            test_runs=len(test_runs),
            production_runs=len(production_runs),
            success_rate=(successful / len(events) * 100) if events else 0.0,
            avg_duration_ms=sum(e.duration_ms for e in events) / len(events),
            last_test_run=last_test,
            last_production_run=last_prod,
            error_counts=error_counts,
        )

    def prune(
        self,
        keep_days: int = 30,
        skill_name: Optional[str] = None,
    ) -> int:
        """
        Prune old diary events.

        Args:
            keep_days: Number of days of events to keep.
            skill_name: Only prune events for this skill.

        Returns:
            Number of events pruned.
        """
        if not self.diary_file.exists():
            return 0

        cutoff = datetime.utcnow() - timedelta(days=keep_days)
        kept_events: List[str] = []
        pruned_count = 0

        with open(self.diary_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    event = DiaryEvent.from_json(line)
                except (json.JSONDecodeError, TypeError):
                    continue

                # Check if should prune
                if skill_name and event.skill_name != skill_name:
                    kept_events.append(line)
                    continue

                event_time = datetime.fromisoformat(
                    event.timestamp.replace("Z", "+00:00")
                ).replace(tzinfo=None)

                if event_time >= cutoff:
                    kept_events.append(line)
                else:
                    pruned_count += 1
                    # Also remove trace file if exists
                    if event.trace_file:
                        trace_path = self.diary_dir / event.trace_file
                        if trace_path.exists():
                            trace_path.unlink()

        # Rewrite diary file
        with open(self.diary_file, "w", encoding="utf-8") as f:
            for line in kept_events:
                f.write(line + "\n")

        return pruned_count

    def get_evidence_report(
        self,
        skill_name: str,
        include_traces: bool = False,
    ) -> Dict[str, Any]:
        """
        Generate an evidence report for a skill.

        Args:
            skill_name: Name of the skill.
            include_traces: Whether to include trace data.

        Returns:
            Evidence report dictionary.
        """
        summary = self.get_summary(skill_name)
        events = self.get_events_for_skill(skill_name)

        # Get recent events
        recent_events = sorted(events, key=lambda e: e.timestamp, reverse=True)[:10]

        report = {
            "skill_name": skill_name,
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "summary": summary.to_dict(),
            "recent_events": [e.to_dict() for e in recent_events],
        }

        if include_traces:
            report["traces"] = []
            for event in recent_events:
                if event.trace_file:
                    trace_path = self.diary_dir / event.trace_file
                    if trace_path.exists():
                        with open(trace_path, "r", encoding="utf-8") as f:
                            trace_data = json.load(f)
                        report["traces"].append({
                            "event_id": event.event_id,
                            "trace_file": event.trace_file,
                            "data": trace_data,
                        })

        return report


def create_gitignore_content() -> str:
    """Generate .gitignore content for .skillspec directory."""
    return """\
# Skill-Spec Runtime Data
# This directory contains runtime evidence and should not be committed

# Diary events (execution history)
diary.jsonl

# Trace files (detailed execution traces)
traces/

# Temporary files
*.tmp
*.bak
"""


def ensure_gitignore(skill_dir: Path) -> None:
    """
    Ensure .skillspec is in .gitignore.

    Args:
        skill_dir: Path to the skill directory.
    """
    gitignore_path = skill_dir / ".gitignore"
    skillspec_entry = ".skillspec/"

    if gitignore_path.exists():
        content = gitignore_path.read_text(encoding="utf-8")
        if skillspec_entry not in content:
            with open(gitignore_path, "a", encoding="utf-8") as f:
                f.write(f"\n# Skill-Spec runtime data\n{skillspec_entry}\n")
    else:
        with open(gitignore_path, "w", encoding="utf-8") as f:
            f.write(f"# Skill-Spec runtime data\n{skillspec_entry}\n")
