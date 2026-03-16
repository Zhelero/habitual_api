from fastapi import Depends
from sqlalchemy.orm import Session

from app.db.deps import get_db
from app.repositories.habit_repository import HabitRepository
from app.services.habit_service import HabitService
from app.services.dashboard_service import DashboardService


def get_habit_repository(
        db: Session = Depends(get_db),
) -> HabitRepository:
    return HabitRepository(db)


def get_habit_service(
        repo: HabitRepository = Depends(get_habit_repository),
) -> HabitService:
    return HabitService(repo)


def get_dashboard_service(
        repo: HabitRepository = Depends(get_habit_repository),
) -> DashboardService:
    return DashboardService(repo)