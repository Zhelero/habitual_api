from fastapi import APIRouter, Depends

from app.api.schemas import DashboardStats
from app.services.dashboard_service import DashboardService
from app.api.dependencies import get_dashboard_service

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

@router.get("/", response_model=DashboardStats)
def get_dashboard(service: DashboardService = Depends(get_dashboard_service)):
    return service.get_dashboard_stats()