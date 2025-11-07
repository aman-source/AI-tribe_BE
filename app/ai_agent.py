"""Natural language to SQL agent powered by OpenAI."""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from typing import Any

from fastapi import HTTPException, status
from openai import AsyncOpenAI, OpenAIError
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from .config import get_settings

logger = logging.getLogger("app.ai_agent")

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
        logger.warning("Blocked AI SQL that did not start with SELECT.")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Generated SQL must be a SELECT statement.",
        )
    if any(word in lowered for word in forbidden):
        logger.warning("Blocked AI SQL containing forbidden keyword.", extra={"sql": stmt})
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Query contains forbidden keywords.",
        )
    if " tasks" not in lowered:
        logger.warning("Blocked AI SQL that does not target tasks table.", extra={"sql": stmt})
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Query must target the tasks table.",
        )
    return stmt


def _strip_code_fence(content: str) -> str:
    stripped = content.strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```(?:json)?", "", stripped, count=1).strip()
        stripped = re.sub(r"```$", "", stripped, count=1).strip()
    return stripped


def _extract_sql_from_content(content: str) -> str:
    cleaned = _strip_code_fence(content)
    payload: dict[str, Any]
    try:
        payload = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise ValueError("Model response is not valid JSON.") from exc

    try:
        sql = payload["sql"]
    except (KeyError, TypeError) as exc:
        raise ValueError("Model response missing 'sql' field.") from exc
    return sql


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

        try:
            completion = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": question},
                ],
                response_format={"type": "json_object"},
                temperature=0,
            )
        except OpenAIError as exc:
            logger.exception("OpenAI chat completion failed.", extra={"question": question})
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="AI provider is unavailable. Retry shortly.",
            ) from exc

        content = completion.choices[0].message.content or ""

        try:
            sql = _extract_sql_from_content(content)
        except ValueError as exc:
            logger.exception(
                "Unable to parse OpenAI response.",
                extra={"question": question, "content_sample": content[:500]},
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Unable to parse model response.",
            ) from exc

        validated_sql = _validate_sql(sql)
        logger.info(
            "Generated SQL from AI question.",
            extra={"question": question, "sql": validated_sql},
        )
        return validated_sql

    async def run_query(self, session: AsyncSession, sql: str) -> list[dict]:
        result = await session.execute(text(sql))
        rows = [dict(row._mapping) for row in result.fetchall()]
        logger.info("Executed AI SQL query.", extra={"sql": sql, "row_count": len(rows)})
        return rows

    async def answer(self, session: AsyncSession, question: str) -> AIQueryResult:
        logger.info("Received AI question.", extra={"question": question})
        sql = await self.build_sql(question)
        rows = await self.run_query(session, sql)
        return AIQueryResult(sql=sql, rows=rows)
