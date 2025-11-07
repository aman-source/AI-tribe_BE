"""SQLAlchemy ORM models."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base declarative class."""


class Task(Base):
    """Task record stored in Postgres."""

    __tablename__ = "tasks"

    task_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    team_name: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    member_name: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    task_title: Mapped[str] = mapped_column(String(256), nullable=False)
    task_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    priority: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    last_updated: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    source_tool: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    cycle_time: Mapped[float | None] = mapped_column(Float, nullable=True)
