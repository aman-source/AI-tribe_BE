"""Seed data used to boot the task repository."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import List

from .models import TaskPriority, TaskRecord, TaskStatus, TaskType


def seed_tasks() -> List[TaskRecord]:
    """Return deterministic sample tasks for local development."""

    now = datetime.now(timezone.utc)
    base_created = now - timedelta(days=7)

    samples = [
        TaskRecord(
            task_id="T-1001",
            team_name="Pulse Analytics",
            member_name="Alice",
            task_title="Add trend graph smoothing",
            task_type=TaskType.FEATURE,
            priority=TaskPriority.HIGH,
            status=TaskStatus.IN_PROGRESS,
            created_at=base_created,
            closed_at=None,
            last_updated=now - timedelta(days=1),
            source_tool="Linear",
            cycle_time=3.5,
        ),
        TaskRecord(
            task_id="T-1002",
            team_name="Pulse Analytics",
            member_name="Bob",
            task_title="Fix stuck tasks query",
            task_type=TaskType.BUG,
            priority=TaskPriority.CRITICAL,
            status=TaskStatus.BLOCKED,
            created_at=base_created + timedelta(days=1),
            closed_at=None,
            last_updated=now - timedelta(hours=6),
            source_tool="Jira",
            cycle_time=4.2,
        ),
        TaskRecord(
            task_id="T-1003",
            team_name="Insights",
            member_name="Carol",
            task_title="Document insight export",
            task_type=TaskType.CHORE,
            priority=TaskPriority.MEDIUM,
            status=TaskStatus.OPEN,
            created_at=base_created + timedelta(days=2),
            closed_at=None,
            last_updated=now - timedelta(hours=3),
            source_tool="Asana",
            cycle_time=2.8,
        ),
        TaskRecord(
            task_id="T-1004",
            team_name="Insights",
            member_name="David",
            task_title="AI summarizer evaluation",
            task_type=TaskType.RESEARCH,
            priority=TaskPriority.HIGH,
            status=TaskStatus.COMPLETED,
            created_at=base_created + timedelta(days=3),
            closed_at=now - timedelta(days=1),
            last_updated=now - timedelta(days=1),
            source_tool="Notion",
            cycle_time=5.1,
        ),
        TaskRecord(
            task_id="T-1005",
            team_name="Platform",
            member_name="Emma",
            task_title="Upgrade ingestion workers",
            task_type=TaskType.FEATURE,
            priority=TaskPriority.CRITICAL,
            status=TaskStatus.CLOSED,
            created_at=base_created + timedelta(days=4),
            closed_at=now - timedelta(hours=12),
            last_updated=now - timedelta(hours=12),
            source_tool="Github",
            cycle_time=6.7,
        ),
    ]

    return samples
