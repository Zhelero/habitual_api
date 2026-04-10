from fastapi import APIRouter, Depends, status
from fastapi.security import HTTPAuthorizationCredentials

from app.api.schemas import AuthRequest, AuthResponse, UserResponse, RefreshRequest, RegisterRequest
from app.core.dependencies import get_auth_service, security, get_current_user
from app.services.auth_service import AuthService
from app.db.models import User

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
    return service.register(data.email, data.password)

@router.post("/login/", response_model=AuthResponse, summary="Login user")
def login(
        data: AuthRequest,
        service: AuthService = Depends(get_auth_service),
):
    return service.login(data.email, data.password)

@router.post("/refresh/", response_model=AuthResponse, summary="Refresh tokens")
def refresh(
        data: RefreshRequest,
        service: AuthService = Depends(get_auth_service),
):
    return service.refresh(data.refresh_token)

@router.post("/logout/", status_code=status.HTTP_204_NO_CONTENT, summary="Logout user")
def logout(
        credentials: HTTPAuthorizationCredentials | None = Depends(security),
        service: AuthService = Depends(get_auth_service),
):
    if not credentials:
        return

    service.logout(credentials.credentials)

@router.get("/me/", response_model=UserResponse, summary="Get current user")
def get_me(user: User = Depends(get_current_user)):
    return user

