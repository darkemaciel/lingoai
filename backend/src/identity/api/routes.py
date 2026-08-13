"""Identity API routes — contracts/rest-api.md "Identity" section:
POST /api/v1/auth/register, POST /api/v1/auth/login, POST /api/v1/auth/refresh.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.ext.asyncio import AsyncSession

from identity.application.auth_service import (
    EmailAlreadyRegisteredError,
    InvalidCredentialsError,
    InvalidRefreshTokenError,
    login,
    refresh_access_token,
    register_user,
)
from identity.infrastructure.security import MAX_PASSWORD_BYTES
from shared_kernel.infrastructure.db import get_db_session
from shared_kernel.infrastructure.rate_limiter import enforce_rate_limit

# T071: every route in this module is unauthenticated and abuse-prone
# (credential stuffing / brute force / spam registration), so all three
# share the same rate limit — applied once here via router-level
# dependencies rather than repeated per-route.
router = APIRouter(prefix="/api/v1/auth", tags=["auth"], dependencies=[Depends(enforce_rate_limit)])


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=MAX_PASSWORD_BYTES)


class RegisterResponse(BaseModel):
    user_id: str
    email: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=MAX_PASSWORD_BYTES)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    expires_in: int


class RefreshRequest(BaseModel):
    refresh_token: str


class AccessTokenResponse(BaseModel):
    access_token: str
    expires_in: int


@router.post("/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
async def register(
    request: RegisterRequest, session: AsyncSession = Depends(get_db_session)
) -> RegisterResponse:
    try:
        user = await register_user(session, email=request.email, password=request.password)
    except EmailAlreadyRegisteredError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="email already registered"
        ) from exc
    return RegisterResponse(user_id=str(user.id), email=user.email)


@router.post("/login", response_model=TokenResponse)
async def login_route(
    request: LoginRequest, session: AsyncSession = Depends(get_db_session)
) -> TokenResponse:
    try:
        tokens = await login(session, email=request.email, password=request.password)
    except InvalidCredentialsError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid credentials"
        ) from exc
    return TokenResponse(
        access_token=tokens.access_token,
        refresh_token=tokens.refresh_token,
        expires_in=tokens.expires_in,
    )


@router.post("/refresh", response_model=AccessTokenResponse)
async def refresh_route(
    request: RefreshRequest, session: AsyncSession = Depends(get_db_session)
) -> AccessTokenResponse:
    try:
        refreshed = await refresh_access_token(session, request.refresh_token)
    except InvalidRefreshTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid or expired refresh token"
        ) from exc
    return AccessTokenResponse(access_token=refreshed.access_token, expires_in=refreshed.expires_in)
