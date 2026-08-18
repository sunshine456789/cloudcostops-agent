from fastapi import APIRouter


router = APIRouter()


@router.get("/")
def root() -> dict[str, str]:
    return {
        "message": "CloudCostOps Agent API is running.",
        "version": "0.6.0-dev",
    }


@router.get("/health")
def health_check() -> dict[str, str]:
    return {
        "status": "healthy",
        "service": "cloudcostops-agent",
        "version": "0.6.0-dev",
    }