"""AI natural language query endpoint."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from ..ai_agent import TaskAIAgent
from ..database import get_session

router = APIRouter(prefix="/ai", tags=["ai"])


class AIQueryRequest(BaseModel):
    question: str = Field(..., min_length=4, description="Natural language question.")


class AIQueryResponse(BaseModel):
    sql: str
    rows: list[dict]


@router.post("/query", response_model=AIQueryResponse)
async def ai_query(
    payload: AIQueryRequest, session: AsyncSession = Depends(get_session)
) -> AIQueryResponse:
    """Answer task-related questions by turning them into SQL."""

    agent = TaskAIAgent()
    result = await agent.answer(session, payload.question)
    return AIQueryResponse(sql=result.sql, rows=result.rows)
