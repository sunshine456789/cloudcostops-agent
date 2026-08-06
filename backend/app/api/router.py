from fastapi import APIRouter

from backend.app.api.routes import (
    agent,
    analysis,
    health,
)


api_router = APIRouter()

api_router.include_router(
    health.router,
    tags=["System"],
)
api_router.include_router(
    analysis.router,
    tags=["Analysis"],
)
api_router.include_router(
    agent.router,
    tags=["Agent"],
)