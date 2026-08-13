"""Reusable FastAPI dependency for extracting the authenticated user from a
Bearer access token (research.md §10 — header-based, so a future mobile
client authenticates identically per NFR-8). Every protected route in every
module should depend on `get_current_user_id` rather than re-implementing
token parsing.
"""

from __future__ import annotations

import uuid

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from identity.infrastructure.security import InvalidTokenError, decode_access_token

_bearer_scheme = HTTPBearer(auto_error=True)


async def get_current_user_id(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer_scheme),
) -> uuid.UUID:
    try:
        return decode_access_token(credentials.credentials)
    except InvalidTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid or expired access token",
        ) from exc
