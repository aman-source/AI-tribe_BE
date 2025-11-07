"""Database-backed task repository."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Sequence
from uuid import uuid4

from sqlalchemy import Select, delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from .db_models import Task
from .models import TaskCreate, TaskRecord, TaskStatus, TaskUpdate


def _ensure_timezone(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


class TaskRepository:
    """Encapsulates CRUD operations for tasks."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    def _base_query(self) -> Select[tuple[Task]]:
        return select(Task)

    async def list(
        self,
        *,
        status: TaskStatus | None = None,
        team_name: str | None = None,
        member_name: str | None = None,
        priority: str | None = None,
        task_type: str | None = None,
        source_tool: str | None = None,
    ) -> Sequence[TaskRecord]:
        stmt = self._base_query()
        if status:
            stmt = stmt.where(Task.status == status.value)
        if team_name:
            stmt = stmt.where(Task.team_name.ilike(f"%{team_name}%"))
        if member_name:
            stmt = stmt.where(Task.member_name.ilike(f"%{member_name}%"))
        if priority:
            stmt = stmt.where(Task.priority == priority)
        if task_type:
            stmt = stmt.where(Task.task_type == task_type)
        if source_tool:
            stmt = stmt.where(Task.source_tool.ilike(f"%{source_tool}%"))

        result = await self.session.execute(stmt.order_by(Task.created_at.desc()))
        tasks = result.scalars().all()
        return [TaskRecord.model_validate(task) for task in tasks]

    async def get(self, task_id: str) -> TaskRecord | None:
        task = await self.session.get(Task, task_id)
        return TaskRecord.model_validate(task) if task else None

    async def create(self, payload: TaskCreate) -> TaskRecord:
        now = datetime.now(timezone.utc)
        data = payload.model_dump(exclude_none=True)
        task_id = data.get("task_id") or str(uuid4())
        status_value = data.get("status", TaskStatus.OPEN.value)
        status_enum = TaskStatus(status_value)

        created_at = _ensure_timezone(data.get("created_at")) or now
        last_updated = _ensure_timezone(data.get("last_updated")) or now
        closed_at = _ensure_timezone(data.get("closed_at"))

        if status_enum in {TaskStatus.CLOSED, TaskStatus.COMPLETED} and not closed_at:
            closed_at = now
        elif status_enum not in {TaskStatus.CLOSED, TaskStatus.COMPLETED}:
            closed_at = None

        task = Task(
            task_id=task_id,
            team_name=data["team_name"],
            member_name=data["member_name"],
            task_title=data["task_title"],
            task_type=data["task_type"],
            priority=data["priority"],
            status=status_enum.value,
            created_at=created_at,
            closed_at=closed_at,
            last_updated=last_updated,
            source_tool=data["source_tool"],
            cycle_time=data.get("cycle_time"),
        )
        self.session.add(task)
        await self.session.commit()
        await self.session.refresh(task)
        return TaskRecord.model_validate(task)

    async def update(self, task_id: str, payload: TaskUpdate) -> TaskRecord | None:
        task = await self.session.get(Task, task_id)
        if not task:
            return None

        now = datetime.now(timezone.utc)
        data = payload.model_dump(exclude_unset=True)

        for field, value in data.items():
            setattr(task, field, value)

        if data.get("status"):
            status_enum = TaskStatus(data["status"])
        else:
            status_enum = TaskStatus(task.status)

        if "created_at" in data:
            task.created_at = _ensure_timezone(task.created_at)
        if "closed_at" in data:
            task.closed_at = _ensure_timezone(task.closed_at)

        if status_enum in {TaskStatus.CLOSED, TaskStatus.COMPLETED}:
            task.closed_at = task.closed_at or now
        else:
            task.closed_at = None

        task.last_updated = now
        await self.session.commit()
        await self.session.refresh(task)
        return TaskRecord.model_validate(task)

    async def delete(self, task_id: str) -> bool:
        stmt = delete(Task).where(Task.task_id == task_id)
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.rowcount > 0
