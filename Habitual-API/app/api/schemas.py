from pydantic import BaseModel, ConfigDict, Field, model_validator

from datetime import date
from typing import Optional

class HabitCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=255)


class HabitResponse(BaseModel):
    id: int
    name: str
    description: str | None = None

    model_config = ConfigDict(from_attributes=True)


class HabitUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=255)

    @model_validator(mode="after")
    def check_at_least_one_field(self):
        if self.name is None and self.description is None:
            raise ValueError("At least one field is required")
        return self

class HabitHeatmap(BaseModel):
    date: date
    done: bool


class HabitStats(BaseModel):
    current_streak: int
    best_streak: int
    completion_last_7_days: float
    completion_last_30_days: float
    last_7_days: list[HabitHeatmap]

    model_config = ConfigDict(from_attributes=True)

class DashboardStats(BaseModel):
    total_habits: int
    completed_today: int
    best_streak: int