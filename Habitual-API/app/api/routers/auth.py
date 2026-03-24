from fastapi import APIRouter, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.api.schemas import AuthRequest, AuthResponse
from app.core.dependencies import get_auth_service, security
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post(
    "/register",
    status_code=status.HTTP_201_CREATED,
    response_model=AuthResponse,
    summary="Register a new user",
)
def register(
        data: AuthRequest,
        service: AuthService = Depends(get_auth_service),
):
    return service.register(data.email, data.password)

@router.post("/login", response_model=AuthResponse)
def login(
        data: AuthRequest,
        service: AuthService = Depends(get_auth_service),
):
    return service.login(data.email, data.password)

@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
        credentials: HTTPAuthorizationCredentials = Depends(security),
        service: AuthService = Depends(get_auth_service),
):
    if credentials:
        service.logout(credentials.credentials)


