"""Entry point for the FastAPI application."""

import logging
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .database import engine
from .db_models import Base
from .models import HealthCheck
from .routers.analytics import router as analytics_router
from .routers.ai import router as ai_router
from .routers.tasks import router as tasks_router

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)


def _allowed_origins() -> list[str]:
    """Return origins from env (comma separated) or defaults."""

    raw = os.getenv("ALLOWED_ORIGINS")
    if raw:
        return [origin.strip() for origin in raw.split(",") if origin.strip()]
    return [
        "http://localhost:8081",  # local dev frontend
        "https://ai-tribe-hackathon2025-ovw3-csvwrs3lc-amans-projects-31c68103.vercel.app",  # deployed frontend
    ]


app = FastAPI(
    title="Tasks API",
    version="0.2.0",
    description="Neon-backed backend service powering the Pulsevo dashboard.",
)

allowed_origins = _allowed_origins()
allow_all = "*" in allowed_origins

# Allow the UI (likely a separate frontend) to hit the API without CORS issues.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if allow_all else allowed_origins,
    allow_credentials=not allow_all,
    allow_methods=["*"],
    allow_headers=["*"],
)

if allow_all:
    logging.warning(
        "CORS configured to allow all origins without credentials; set ALLOWED_ORIGINS to tighten."
    )
else:
    logging.info("CORS enabled for origins: %s", allowed_origins)

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
