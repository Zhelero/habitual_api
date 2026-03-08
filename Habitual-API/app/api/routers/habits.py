from fastapi import APIRouter, Depends, HTTPException

from app.api.schemas import (HabitCreate, HabitResponse, HabitStats, HabitHeatmap, HabitUpdate)
from app.services.habit_service import HabitService
from app.api.dependencies import get_habit_service

router = APIRouter(prefix="/habits", tags=["habits"])


@router.post("/", response_model=HabitResponse, status_code=201)
def create_habit(
        habit: HabitCreate,
        service: HabitService = Depends(get_habit_service),
):
    try:
        return service.create_habit(
            name=habit.name,
            description=habit.description
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.patch("/{habit_id}", response_model=HabitResponse)
def update_habit(
        habit_id: int,
        payload: HabitUpdate,
        service: HabitService = Depends(get_habit_service),
):
    try:
        return service.update_habit(
            habit_id,
            payload.model_dump(exclude_unset=True)
        )
    except ValueError as e:
        message = str(e)

        if message == "Habit not found":
            raise HTTPException(status_code=404, detail=message)

        raise HTTPException(status_code=400, detail=message)


@router.get("/", response_model=list[HabitResponse])
def get_habits(
        service: HabitService = Depends(get_habit_service),
):
    return service.get_habits()

# Delete

@router.delete("/{habit_id}", status_code=204)
def delete_habit(
        habit_id: int,
        service: HabitService = Depends(get_habit_service),
):
    try:
        service.delete_habit(habit_id)

    except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))


# Mark done

@router.post("/{habit_id}/done", status_code=201)
def mark_done(
        habit_id: int,
        service: HabitService = Depends(get_habit_service),
):
    try:
        service.mark_done(habit_id)
        return {"message": "Habit marked as done"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

# Undo mark done

@router.delete("/{habit_id}/done", status_code=204)
def undo_done(
        habit_id: int,
        service: HabitService = Depends(get_habit_service),
):
    try:
        service.undo_done(habit_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

# Stats

@router.get("/{habit_id}/stats", response_model=HabitStats)
def get_stats(
        habit_id: int,
        service: HabitService = Depends(get_habit_service),
):
    try:
        return service.get_stats(habit_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.get("/{habit_id}/heatmap", response_model=list[HabitHeatmap])
def get_heatmap(
        habit_id: int,
        service: HabitService = Depends(get_habit_service),
):
    try:
        return service.get_heatmap(habit_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
