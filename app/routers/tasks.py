"""Task-related API routes."""

from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status

from ..dependencies import get_task_repository
from ..models import (
    TaskCreate,
    TaskRecord,
    TaskStatus,
    TaskType,
    TaskPriority,
    TaskUpdate,
)
from ..repository import TaskRepository

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.get("/", response_model=List[TaskRecord])
async def list_tasks(
    *,
    repo: TaskRepository = Depends(get_task_repository),
    status_filter: TaskStatus | None = Query(
        None, alias="status", description="Filter by task status."
    ),
    team_name: str | None = Query(None, description="Filter by team name."),
    member_name: str | None = Query(None, description="Filter by member name."),
    priority: TaskPriority | None = Query(None, description="Filter by priority."),
    task_type: TaskType | None = Query(None, description="Filter by task type."),
    source_tool: str | None = Query(None, description="Filter by originating tool."),
) -> List[TaskRecord]:
    """Return all tasks honoring optional filters."""

    return await repo.list(
        status=status_filter,
        team_name=team_name,
        member_name=member_name,
        priority=priority.value if priority else None,
        task_type=task_type.value if task_type else None,
        source_tool=source_tool,
    )


@router.post("/", response_model=TaskRecord, status_code=status.HTTP_201_CREATED)
async def create_task(payload: TaskCreate, repo: TaskRepository = Depends(get_task_repository)) -> TaskRecord:
    """Create a new task."""

    return await repo.create(payload)


@router.get("/{task_id}", response_model=TaskRecord)
async def get_task(task_id: str, repo: TaskRepository = Depends(get_task_repository)) -> TaskRecord:
    """Fetch a single task by identifier."""

    task = await repo.get(task_id)
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found.")
    return task


@router.patch("/{task_id}", response_model=TaskRecord)
async def update_task(
    task_id: str, payload: TaskUpdate, repo: TaskRepository = Depends(get_task_repository)
) -> TaskRecord:
    """Patch an existing task."""

    task = await repo.update(task_id, payload)
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found.")
    return task


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(task_id: str, repo: TaskRepository = Depends(get_task_repository)) -> None:
    """Delete a task."""

    deleted = await repo.delete(task_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found.")
