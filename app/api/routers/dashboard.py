import logging
from fastapi import APIRouter, Depends

from app.api.schemas import DashboardStats
from app.services.dashboard_service import DashboardService
from app.core.dependencies import get_dashboard_service, get_current_user
from app.db.models import User

logger = logging.getLogger("app.dashboard")

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get(
    "/",
    response_model=DashboardStats,
    summary="Get dashboard stats",
)
def get_dashboard(
    current_user: User = Depends(get_current_user),
    service: DashboardService = Depends(get_dashboard_service),
):
    stats = service.get_dashboard_stats(current_user.id)

    logger.info("Dashboard stats received user_id=%s", current_user.id)

    return stats
