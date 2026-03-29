from fastapi import APIRouter, Depends, Query, status

from app.db.models import User
from app.services.habit_service import HabitService
from app.core.dependencies import get_habit_service, get_current_user
from app.api.schemas import (
    HabitCreate,
    HabitResponse,
    HabitStats,
    HabitHeatmap,
    HabitUpdate,
    PaginatedHabits,
)

router = APIRouter(prefix="/habits", tags=["habits"])

# Create

@router.post(
    "/",
    response_model=HabitResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create habit"
)
def create_habit(
        habit: HabitCreate,
        user: User = Depends(get_current_user),
        service: HabitService = Depends(get_habit_service),
):
    return service.create_habit(user.id, habit.name, habit.description)

# List (pagination)

@router.get(
    "/",
    response_model=PaginatedHabits,
    summary="List habits (paginated)",
)
def get_habits(
        limit: int = Query(20, ge=1, le=100),
        offset: int = Query(0, ge=0),
        user: User = Depends(get_current_user),
        service: HabitService = Depends(get_habit_service),
):
    return service.get_habits(user.id, limit, offset)

# Get habit

@router.get(
    "/{habit_id}/",
    response_model=HabitResponse,
    summary="Get habit by id")
def get_habit(
        habit_id: int,
        user: User = Depends(get_current_user),
        service: HabitService = Depends(get_habit_service),
):
    return service.get_habit(user.id, habit_id)

# Update

@router.patch(
    "/{habit_id}/",
    response_model=HabitResponse,
    summary="Update habit")
def update_habit(
        habit_id: int,
        payload: HabitUpdate,
        user: User = Depends(get_current_user),
        service: HabitService = Depends(get_habit_service),
):
    return service.update_habit(
        user.id,
        habit_id,
        payload.model_dump(exclude_unset=True)
    )

# Delete

@router.delete(
    "/{habit_id}/",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete habit"
)
def delete_habit(
        habit_id: int,
        user: User = Depends(get_current_user),
        service: HabitService = Depends(get_habit_service),
):
    service.delete_habit(user.id, habit_id)
    return None

# Mark done

@router.post(
    "/{habit_id}/done/",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Mark habit as done",
)
def mark_done(
        habit_id: int,
        user: User = Depends(get_current_user),
        service: HabitService = Depends(get_habit_service),
):
    service.mark_done(user.id, habit_id)
    return None

# Undo mark done

@router.delete(
    "/{habit_id}/done/",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Undo habit completion",
)
def undo_done(
        habit_id: int,
        user: User = Depends(get_current_user),
        service: HabitService = Depends(get_habit_service),
):
    service.undo_done(user.id, habit_id)
    return None

# Stats

@router.get(
    "/{habit_id}/stats/",
    response_model=HabitStats,
    summary="Get habit statistics",
)
def get_stats(
        habit_id: int,
        user: User = Depends(get_current_user),
        service: HabitService = Depends(get_habit_service),
):
    return service.get_stats(user.id, habit_id)

# Heatmap

@router.get(
    "/{habit_id}/heatmap/",
    response_model=list[HabitHeatmap],
    summary="Get habit heatmap (last 30 days)"
)
def get_heatmap(
        habit_id: int,
        user: User = Depends(get_current_user),
        service: HabitService = Depends(get_habit_service),
):
    return service.get_heatmap(user.id, habit_id)

