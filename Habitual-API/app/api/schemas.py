from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator, field_validator
from datetime import datetime, date

from app.core.exceptions import AtLeastOneFieldError, NameCannotBeEmptyError

class AuthRequest(BaseModel):
    email: EmailStr
    password: str

class AuthResponse(BaseModel):
    access_token: str
    token_type: str
    user_id: int

class HabitCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: str | None = Field(None, max_length=255)

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str | None):
        value = _normalize_str(value)

        if not value:
            raise NameCannotBeEmptyError("Name can't be empty")

        return value

    @field_validator("description")
    @classmethod
    def validate_description(cls, value: str | None):
        return _normalize_str(value)


class HabitResponse(BaseModel):
    id: int
    name: str
    description: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class HabitUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=100)
    description: str | None = Field(None, max_length=255)

    @model_validator(mode="after")
    def check_at_least_one_field(self):
        if self.name is None and self.description is None:
            raise AtLeastOneFieldError("At least one field is required")
        return self

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str):
        value = _normalize_str(value)

        if not value:
            raise NameCannotBeEmptyError("Name can't be empty")

        return value

    @field_validator("description")
    @classmethod
    def validate_description(cls, value: str | None):
        return _normalize_str(value)

class HabitHeatmap(BaseModel):
    date: date
    done: bool


class HabitStats(BaseModel):
    current_streak: int
    total_logs: int | None = None
    best_streak: int
    completion_last_7_days: float
    completion_last_30_days: float
    last_7_days: list[HabitHeatmap]

class DashboardStats(BaseModel):
    total_habits: int
    completed_today: int
    best_streak: int

class PaginatedHabits(BaseModel):
    items: list[HabitResponse]
    total: int
    limit: int
    offset: int

# HELPERS

def _normalize_str(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip()
    return value or None