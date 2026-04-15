"""
API Router for Health Checks
"""

from fastapi import APIRouter
from datetime import datetime
from app.core.config import settings
from app.schemas import HealthResponse

router = APIRouter()


@router.get("/", response_model=HealthResponse)
async def health_check():
    """Check service health status"""
    # Check dependent services (implement actual checks in production)
    services = {
        "database": True,  # TODO: Add actual database check
        "redis": True,     # TODO: Add actual Redis check
        "celery": True,    # TODO: Add actual Celery check
    }
    
    overall_status = "healthy" if all(services.values()) else "degraded"
    
    return HealthResponse(
        status=overall_status,
        version=settings.VERSION,
        timestamp=datetime.utcnow(),
        services=services,
    )


@router.get("/ready")
async def readiness_check():
    """Check if service is ready to accept requests"""
    return {"ready": True}


@router.get("/live")
async def liveness_check():
    """Check if service is alive"""
    return {"alive": True}
