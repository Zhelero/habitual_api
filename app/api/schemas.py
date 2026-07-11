from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    model_validator,
    field_validator,
)
from datetime import datetime, date
from typing import Literal

from app.core.enums import HabitColor
from app.services.helpers import normalize_name, normalize_description
from app.core.exceptions import AtLeastOneFieldError, NameCannotBeEmptyError


class AuthRequest(BaseModel):
    email: EmailStr
    password: str


class AuthResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: Literal["bearer"]
    user_id: int


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str):
        if not v or not v.strip():
            raise ValueError("Password cannot be empty")

        if len(v.strip()) < 8:
            raise ValueError("Password must be at least 8 characters")

        if len(v) > 128:
            raise ValueError("Password must be at most 128 characters")

        return v


class RefreshRequest(BaseModel):
    refresh_token: str = Field(
        min_length=1,
        description="JWT refresh token",
    )


class UserResponse(BaseModel):
    id: int
    email: EmailStr

    model_config = ConfigDict(from_attributes=True)


class HabitCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: str | None = Field(None, max_length=255)
    color: HabitColor | None = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str | None):
        value = normalize_name(value)

        if not value:
            raise NameCannotBeEmptyError("Name can't be empty")

        return value

    @field_validator("description")
    @classmethod
    def validate_description(cls, value: str | None):
        return normalize_description(value)


class HabitResponse(BaseModel):
    id: int
    name: str
    description: str | None = None
    color: str | None = None
    created_at: datetime
    updated_at: datetime
    is_archived: bool
    model_config = ConfigDict(from_attributes=True)


class HabitUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=100)
    description: str | None = Field(None, max_length=255)
    color: HabitColor | None = None

    @model_validator(mode="after")
    def check_at_least_one_field(self):
        if not self.model_fields_set:
            raise AtLeastOneFieldError("At least one field is required")
        return self

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str | None):
        value = normalize_name(value)

        if not value:
            raise NameCannotBeEmptyError("Name can't be empty")

        return value

    @field_validator("description")
    @classmethod
    def validate_description(cls, value: str | None):
        return normalize_description(value)


class HabitDoneRequest(BaseModel):
    note: str | None = Field(None, max_length=500)


class HabitHeatmap(BaseModel):
    date: date
    done: bool


class HabitStats(BaseModel):
    current_streak: int
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
