"""Natural language to SQL agent powered by OpenAI."""

from __future__ import annotations

import json
from dataclasses import dataclass

from fastapi import HTTPException, status
from openai import AsyncOpenAI
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from .config import get_settings

SCHEMA_SUMMARY = """
You can only query a single Postgres table named tasks with the following columns and types:
- task_id (varchar, primary key)
- team_name (text)
- member_name (text)
- task_title (text)
- task_type (text)
- priority (text)
- status (text: open, in_progress, blocked, completed, closed)
- created_at (timestamptz)
- closed_at (timestamptz, nullable)
- last_updated (timestamptz)
- source_tool (text)
- cycle_time (float, nullable)
"""

SQL_GUARDRAILS = (
    "Only write read-only SELECT queries. Never modify data. "
    "Always reference the tasks table and include limit 100 if not specified."
)


def _validate_sql(sql: str) -> str:
    stmt = sql.strip().rstrip(";")
    lowered = stmt.lower()
    forbidden = ["insert", "update", "delete", "drop", "alter", "create", "truncate"]
    if not lowered.startswith("select"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Generated SQL must be a SELECT statement.",
        )
    if any(word in lowered for word in forbidden):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Query contains forbidden keywords.",
        )
    if " tasks" not in lowered:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Query must target the tasks table.",
        )
    return stmt


@dataclass
class AIQueryResult:
    sql: str
    rows: list[dict]


class TaskAIAgent:
    """Converts natural language to safe SQL and executes it."""

    def __init__(self) -> None:
        settings = get_settings()
        if not settings.openai_api_key:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="OPENAI_API_KEY not configured.",
            )
        self.model = settings.openai_model
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)

    async def build_sql(self, question: str) -> str:
        system_prompt = (
            "You translate product analytics questions into SQL for Postgres.\n"
            f"{SCHEMA_SUMMARY}\n{SQL_GUARDRAILS}\n"
            'Respond with JSON: {"sql": "SELECT ..."}'
        )

        completion = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": question},
            ],
            temperature=0,
        )
        content = completion.choices[0].message.content

        try:
            payload = json.loads(content)
            sql = payload["sql"]
        except (json.JSONDecodeError, KeyError, TypeError) as exc:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Unable to parse model response.",
            ) from exc

        return _validate_sql(sql)

    async def run_query(self, session: AsyncSession, sql: str) -> list[dict]:
        result = await session.execute(text(sql))
        rows = [dict(row._mapping) for row in result.fetchall()]
        return rows

    async def answer(self, session: AsyncSession, question: str) -> AIQueryResult:
        sql = await self.build_sql(question)
        rows = await self.run_query(session, sql)
        return AIQueryResult(sql=sql, rows=rows)
