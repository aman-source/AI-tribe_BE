"""Dependency helpers for FastAPI routes."""

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from .database import get_session
from .repository import TaskRepository


async def get_task_repository(
    session: AsyncSession = Depends(get_session),
) -> TaskRepository:
    """Return a repository bound to the current database session."""

    return TaskRepository(session)
