from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from jose import JWTError

from app.db.deps import get_db
from app.core.jwt import decode_token
from app.db.models import User
from app.repositories.habit_repository import HabitRepository
from app.repositories.user_repository import UserRepository
from app.services.habit_service import HabitService
from app.services.dashboard_service import DashboardService
from app.services.auth_service import AuthService

security = HTTPBearer(auto_error=False)

UNAUTHORIZED = "Invalid token"
NOT_AUTHENTICATED = "Not authenticated"
USER_NOT_FOUND = "User not found"

# REPOSITORIES

def get_user_repository(
        db: Session = Depends(get_db),
) -> UserRepository:
    return UserRepository(db)

def get_habit_repository(
        db: Session = Depends(get_db),
) -> HabitRepository:
    return HabitRepository(db)

# SERVICES

def get_auth_service(
        repo: UserRepository = Depends(get_user_repository),
) -> AuthService:
    return AuthService(repo)

def get_habit_service(
        repo: HabitRepository = Depends(get_habit_repository),
) -> HabitService:
    return HabitService(repo)


def get_dashboard_service(
        repo: HabitRepository = Depends(get_habit_repository),
) -> DashboardService:
    return DashboardService(repo)

# AUTH

def get_current_user(
        credentials: HTTPAuthorizationCredentials = Depends(security),
        repo: UserRepository = Depends(get_user_repository),
) -> User:

    if not credentials:
        raise HTTPException(status_code=401, detail=NOT_AUTHENTICATED)

    token = credentials.credentials

    try:
        payload = decode_token(token)
    except JWTError:
        raise HTTPException(status_code=401, detail=UNAUTHORIZED)

    user_id_str = payload.get("sub")
    if not user_id_str:
        raise HTTPException(status_code=401, detail=UNAUTHORIZED)

    try:
        user_id = int(user_id_str)
    except ValueError:
        raise HTTPException(status_code=401, detail=UNAUTHORIZED)

    user = repo.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=401, detail=USER_NOT_FOUND)

    return user