"""Analytics and KPI endpoints."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Dict, List

from fastapi import APIRouter, Depends
from sqlalchemy import DateTime, case, cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_session
from ..db_models import Task
from ..models import TaskStatus

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/dashboard")
async def dashboard(session: AsyncSession = Depends(get_session)) -> Dict[str, object]:
    """Return all KPI blocks required by the single-page dashboard."""

    now = datetime.now(timezone.utc)
    start_today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    start_hour = now - timedelta(hours=1)
    trend_window_start = start_today - timedelta(days=6)

    total_tasks = await session.scalar(select(func.count()).select_from(Task)) or 0

    created_at_ts = cast(Task.created_at, DateTime(timezone=True))
    closed_at_ts = cast(Task.closed_at, DateTime(timezone=True))
    last_updated_ts = cast(Task.last_updated, DateTime(timezone=True))

    open_tasks = (
        await session.scalar(select(func.count()).where(Task.status == TaskStatus.OPEN.value))
        or 0
    )
    in_progress_tasks = (
        await session.scalar(
            select(func.count()).where(Task.status == TaskStatus.IN_PROGRESS.value)
        )
        or 0
    )

    closed_total = await session.scalar(
        select(func.count()).where(Task.status.in_([TaskStatus.CLOSED.value, TaskStatus.COMPLETED.value]))
    ) or 0

    closed_today = (
        await session.scalar(
            select(func.count()).where(
                Task.closed_at.is_not(None),
                closed_at_ts >= start_today,
                closed_at_ts < start_today + timedelta(days=1),
            )
        )
        or 0
    )

    closed_this_hour = (
        await session.scalar(
            select(func.count()).where(
                Task.closed_at.is_not(None),
                closed_at_ts >= start_hour,
                closed_at_ts <= now,
            )
        )
        or 0
    )

    completion_rate = round((closed_total / total_tasks) * 100, 2) if total_tasks else 0.0

    status_counts = (
        await session.execute(select(Task.status, func.count()).group_by(Task.status))
    ).all()
    task_distribution = []
    for status, count in status_counts:
        percentage = round((count / total_tasks) * 100, 2) if total_tasks else 0.0
        task_distribution.append(
            {"status": status, "count": count, "percentage": percentage}
        )

    created_rows = (
        await session.execute(
            select(func.date_trunc("day", created_at_ts).label("bucket"), func.count())
            .where(created_at_ts >= trend_window_start)
            .group_by("bucket")
            .order_by("bucket")
        )
    ).all()
    created_map = {row.bucket.date().isoformat(): row.count for row in created_rows}

    completed_rows = (
        await session.execute(
            select(func.date_trunc("day", closed_at_ts).label("bucket"), func.count())
            .where(
                Task.closed_at.is_not(None),
                closed_at_ts >= trend_window_start,
            )
            .group_by("bucket")
            .order_by("bucket")
        )
    ).all()
    completed_map = {row.bucket.date().isoformat(): row.count for row in completed_rows}

    in_progress_rows = (
        await session.execute(
            select(func.date_trunc("day", last_updated_ts).label("bucket"), func.count())
            .where(
                Task.status == TaskStatus.IN_PROGRESS.value,
                last_updated_ts >= trend_window_start,
            )
            .group_by("bucket")
            .order_by("bucket")
        )
    ).all()
    in_progress_map = {row.bucket.date().isoformat(): row.count for row in in_progress_rows}

    trend_data: List[Dict[str, object]] = []
    for offset in range(0, 7):
        day = (trend_window_start + timedelta(days=offset)).date().isoformat()
        trend_data.append(
            {
                "date": day,
                "tasks_created": created_map.get(day, 0),
                "tasks_completed": completed_map.get(day, 0),
                "tasks_in_progress": in_progress_map.get(day, 0),
            }
        )

    team_rows = (
        await session.execute(
            select(
                Task.team_name,
                func.count(
                    case(
                        (
                            Task.status.in_(
                                [TaskStatus.CLOSED.value, TaskStatus.COMPLETED.value]
                            ),
                            1,
                        ),
                        else_=None,
                    )
                ).label("completed"),
                func.count(
                    case((Task.status == TaskStatus.IN_PROGRESS.value, 1), else_=None)
                ).label("in_progress"),
                func.count(case((Task.status == TaskStatus.OPEN.value, 1), else_=None)).label("open"),
            ).group_by(Task.team_name)
        )
    ).all()

    team_performance = [
        {
            "team_name": row.team_name,
            "completed": row.completed or 0,
            "in_progress": row.in_progress or 0,
            "open": row.open or 0,
        }
        for row in team_rows
    ]

    return {
        "kpis": {
            "open_tasks": open_tasks,
            "in_progress": in_progress_tasks,
            "closed_today": closed_today,
            "closed_this_hour": closed_this_hour,
            "completion_rate": completion_rate,
        },
        "task_distribution": task_distribution,
        "trend": trend_data,
        "team_performance": team_performance,
    }


@router.get("/task-management")
async def task_management(session: AsyncSession = Depends(get_session)) -> List[Dict[str, object]]:
    """Return per-member task stats used by the task management view."""

    rows = (
        await session.execute(
            select(
                Task.member_name.label("name"),
                func.count().label("total_assigned"),
                func.count(
                    case((Task.status == TaskStatus.IN_PROGRESS.value, 1), else_=None)
                ).label("ongoing"),
                func.count(
                    case(
                        (
                            Task.status.in_(
                                [TaskStatus.COMPLETED.value, TaskStatus.CLOSED.value]
                            ),
                            1,
                        ),
                        else_=None,
                    )
                ).label("completed"),
            ).group_by(Task.member_name)
        )
    ).all()

    response: List[Dict[str, object]] = []
    for row in rows:
        total = row.total_assigned or 0
        completed = row.completed or 0
        ongoing = row.ongoing or 0
        trend = round((completed / total) * 100, 2) if total else 0.0
        response.append(
            {
                "name": row.name,
                "total_assigned": total,
                "ongoing": ongoing,
                "completed": completed,
                "trend_percent": trend,
            }
        )

    return response
