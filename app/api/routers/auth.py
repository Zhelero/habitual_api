import logging
from fastapi import APIRouter, Depends, status
from fastapi.security import HTTPAuthorizationCredentials

from app.api.schemas import (
    AuthRequest,
    AuthResponse,
    UserResponse,
    RefreshRequest,
    RegisterRequest,
)
from app.core.dependencies import get_auth_service, security, get_current_user
from app.services.auth_service import AuthService
from app.db.models import User

logger = logging.getLogger("app.auth")

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/register/",
    status_code=status.HTTP_201_CREATED,
    response_model=AuthResponse,
    summary="Register a new user",
)
def register(
    data: RegisterRequest,
    service: AuthService = Depends(get_auth_service),
):
    logger.info("Register attempt email=%s", data.email)

    response = service.register(data.email, data.password)

    logger.info("Register success email=%s", data.email)
    return response


@router.post("/login/", response_model=AuthResponse, summary="Login user")
def login(
    data: AuthRequest,
    service: AuthService = Depends(get_auth_service),
):
    logger.info("Login attempt email=%s", data.email)
    response = service.login(data.email, data.password)

    logger.info("Login success email=%s", data.email)
    return response


@router.post("/refresh/", response_model=AuthResponse, summary="Refresh tokens")
def refresh(
    data: RefreshRequest,
    service: AuthService = Depends(get_auth_service),
):
    response = service.refresh(data.refresh_token)

    logger.info("Token refreshed")
    return response


@router.post("/logout/", status_code=status.HTTP_204_NO_CONTENT, summary="Logout user")
def logout(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    service: AuthService = Depends(get_auth_service),
):
    if not credentials:
        logger.warning("Logout without credentials")
        return

    logger.info("Logout attempt")
    service.logout(credentials.credentials)
    logger.info("Logout success")


@router.get("/me/", response_model=UserResponse, summary="Get current user")
def get_me(user: User = Depends(get_current_user)):
    logger.debug("Get current user user_id=%s", user.id)
    return user
