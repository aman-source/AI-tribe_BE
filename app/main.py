"""Entry point for the FastAPI application."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .database import engine
from .db_models import Base
from .models import HealthCheck
from .routers.analytics import router as analytics_router
from .routers.ai import router as ai_router
from .routers.tasks import router as tasks_router

app = FastAPI(
    title="Tasks API",
    version="0.2.0",
    description="Neon-backed backend service powering the Pulsevo dashboard.",
)

# Allow the UI (likely a separate frontend) to hit the API without CORS issues.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(tasks_router)
app.include_router(analytics_router)
app.include_router(ai_router)


@app.on_event("startup")
async def on_startup() -> None:
    """Create database schema automatically if it doesn't exist."""

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


@app.get("/health", response_model=HealthCheck, tags=["health"])
async def health() -> HealthCheck:
    """Simple readiness endpoint used by monitors."""

    return HealthCheck(status="ok")
