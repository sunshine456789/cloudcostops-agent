from fastapi import APIRouter

from backend.app.api.routes import (
    agent,
    analysis,
    health,
    runs,
)


# ============================================================
# Main API Router
# ============================================================

api_router = APIRouter()


# ============================================================
# System
# ============================================================

api_router.include_router(
    health.router,
    tags=["System"],
)


# ============================================================
# Analysis
# ============================================================

api_router.include_router(
    analysis.router,
    tags=["Analysis"],
)


# ============================================================
# Agent
# ============================================================

api_router.include_router(
    agent.router,
    tags=["Agent"],
)


# ============================================================
# Agent Run Management
# ============================================================

api_router.include_router(
    runs.router,
    prefix="/runs",
    tags=["Agent Runs"],
)