from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.db.deps import get_db
from app.core.jwt import decode_token
from app.db.models import User
from app.repositories.habit_repository import HabitRepository
from app.repositories.user_repository import UserRepository
from app.repositories.blacklist_repository import TokenBlacklistRepository
from app.services.habit_service import HabitService
from app.services.dashboard_service import DashboardService
from app.services.auth_service import AuthService
from app.core.exceptions import InvalidTokenError, TokenRevokedError

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


# TOKEN BLACKLIST

def get_blacklist_repository(
        db: Session = Depends(get_db),
) -> TokenBlacklistRepository:
    return TokenBlacklistRepository(db)


# SERVICES

def get_auth_service(
        repo: UserRepository = Depends(get_user_repository),
        blacklist_repo: TokenBlacklistRepository = Depends(get_blacklist_repository),
) -> AuthService:
    return AuthService(repo, blacklist_repo)

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
        blacklist_repo: TokenBlacklistRepository = Depends(get_blacklist_repository),
) -> User:

    if not credentials:
        raise HTTPException(status_code=401, detail=NOT_AUTHENTICATED)

    token = credentials.credentials.strip()

    try:
        payload = decode_token(
            token,
            expected_type="access",
            blacklist_repo=blacklist_repo
        )
    except InvalidTokenError:
        raise HTTPException(status_code=401, detail=UNAUTHORIZED)
    except TokenRevokedError:
        raise HTTPException(status_code=401, detail=UNAUTHORIZED)

    try:
        user_id = int(payload["sub"])
    except (KeyError, TypeError):
        raise HTTPException(status_code=401, detail=UNAUTHORIZED)

    user = repo.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=401, detail=USER_NOT_FOUND)

    return user