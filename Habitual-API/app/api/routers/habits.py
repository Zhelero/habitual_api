from fastapi import APIRouter, Depends, Query

from app.services.habit_service import HabitService
from app.api.dependencies import get_habit_service
from app.api.schemas import (
    HabitCreate,
    HabitResponse,
    HabitStats,
    HabitHeatmap,
    HabitUpdate,
    PaginatedHabits,
)

router = APIRouter(prefix="/habits", tags=["habits"])


@router.post("/", response_model=HabitResponse, status_code=201)
def create_habit(
        habit: HabitCreate,
        service: HabitService = Depends(get_habit_service),
):
    return service.create_habit(
        name=habit.name,
        description=habit.description,
    )


@router.patch("/{habit_id}", response_model=HabitResponse)
def update_habit(
        habit_id: int,
        payload: HabitUpdate,
        service: HabitService = Depends(get_habit_service),
):
    return service.update_habit(
        habit_id,
        payload.model_dump(exclude_unset=True)
    )


@router.get("/", response_model=PaginatedHabits)
def get_habits(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    service: HabitService = Depends(get_habit_service),
):
    return service.get_habits_paginated(limit, offset)

# Delete

@router.delete("/{habit_id}", status_code=204)
def delete_habit(
        habit_id: int,
        service: HabitService = Depends(get_habit_service),
):
    service.delete_habit(habit_id)

# Mark done

@router.post("/{habit_id}/done", status_code=204)
def mark_done(
        habit_id: int,
        service: HabitService = Depends(get_habit_service),
):
    service.mark_done(habit_id)

# Undo mark done

@router.delete("/{habit_id}/done", status_code=204)
def undo_done(
        habit_id: int,
        service: HabitService = Depends(get_habit_service),
):
    service.undo_done(habit_id)

# Stats

@router.get("/{habit_id}/stats", response_model=HabitStats)
def get_stats(
        habit_id: int,
        service: HabitService = Depends(get_habit_service),
):
    return service.get_stats(habit_id)


@router.get("/{habit_id}/heatmap", response_model=list[HabitHeatmap])
def get_heatmap(
        habit_id: int,
        service: HabitService = Depends(get_habit_service),
):
    return service.get_heatmap(habit_id)

