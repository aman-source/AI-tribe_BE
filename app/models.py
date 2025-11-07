"""Domain and API models for the task backend."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Dict, Optional

from pydantic import BaseModel, ConfigDict, Field


class TaskStatus(str, Enum):
    """Supported task states."""

    OPEN = "open"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    COMPLETED = "completed"
    CLOSED = "closed"


class TaskPriority(str, Enum):
    """Supported task priorities."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class TaskType(str, Enum):
    """Supported task categories."""

    FEATURE = "feature"
    BUG = "bug"
    IMPROVEMENT = "improvement"
    RESEARCH = "research"
    CHORE = "chore"


class TaskBase(BaseModel):
    """Fields shared across create/update/read models."""

    team_name: str = Field(..., min_length=1)
    member_name: str = Field(..., min_length=1)
    task_title: str = Field(..., min_length=1)
    task_type: TaskType
    priority: TaskPriority
    status: TaskStatus = TaskStatus.OPEN
    created_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None
    last_updated: Optional[datetime] = None
    source_tool: str = Field(..., min_length=1)
    cycle_time: Optional[float] = Field(None, ge=0, description="Cycle time in days")


class TaskRecord(TaskBase):
    """Represents a stored task."""

    task_id: str
    model_config = ConfigDict(from_attributes=True)


class TaskCreate(TaskBase):
    """Payload used to create a new task."""

    task_id: Optional[str] = None


class TaskUpdate(BaseModel):
    """Payload used to partially update a task."""

    team_name: Optional[str] = None
    member_name: Optional[str] = None
    task_title: Optional[str] = None
    task_type: Optional[TaskType] = None
    priority: Optional[TaskPriority] = None
    status: Optional[TaskStatus] = None
    created_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None
    source_tool: Optional[str] = None
    cycle_time: Optional[float] = Field(None, ge=0)


class TaskMetrics(BaseModel):
    """Aggregated information for dashboards."""

    total_tasks: int
    open_tasks: int
    in_progress_tasks: int
    blocked_tasks: int
    completed_tasks: int
    average_cycle_time: Optional[float]
    team_distribution: Dict[str, int]
    member_distribution: Dict[str, int]


class HealthCheck(BaseModel):
    """Simple health check payload."""

    status: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
