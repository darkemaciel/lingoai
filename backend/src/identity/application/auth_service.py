"""Register/login/refresh use cases (identity module application layer).

Request/response shapes are fixed by contracts/rest-api.md's Identity
section. Kept separate from FastAPI (see identity/api/routes.py) so the
logic is testable without an HTTP layer.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from identity.infrastructure.models import RefreshToken, User
from identity.infrastructure.security import (
    create_access_token,
    generate_refresh_token,
    hash_password,
    hash_refresh_token,
    verify_password,
)

# contracts/rest-api.md's POST /auth/register only collects {email, password}
# — it does not collect a timezone, even though data-model.md's User.timezone
# is NOT NULL (needed later for streak day-boundary calculation, research.md
# §7). Defaulting to UTC here is a deliberate placeholder until a future
# profile-settings endpoint lets the student set their real timezone; it does
# not block this slice's acceptance criteria.
_DEFAULT_TIMEZONE = "UTC"


class EmailAlreadyRegisteredError(Exception):
    pass


class InvalidCredentialsError(Exception):
    pass


class InvalidRefreshTokenError(Exception):
    pass


@dataclass
class IssuedTokens:
    access_token: str
    refresh_token: str
    expires_in: int


@dataclass
class RefreshedAccessToken:
    access_token: str
    expires_in: int


async def register_user(session: AsyncSession, email: str, password: str) -> User:
    existing = await session.scalar(select(User).where(User.email == email))
    if existing is not None:
        raise EmailAlreadyRegisteredError(email)

    user = User(
        id=uuid.uuid4(),
        email=email,
        password_hash=hash_password(password),
        timezone=_DEFAULT_TIMEZONE,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


async def _issue_tokens_for(session: AsyncSession, user: User) -> IssuedTokens:
    access_token, expires_in = create_access_token(user.id)
    raw_refresh_token, token_hash, expires_at = generate_refresh_token()
    session.add(
        RefreshToken(
            id=uuid.uuid4(),
            user_id=user.id,
            token_hash=token_hash,
            expires_at=expires_at,
        )
    )
    await session.commit()
    return IssuedTokens(
        access_token=access_token, refresh_token=raw_refresh_token, expires_in=expires_in
    )


async def login(session: AsyncSession, email: str, password: str) -> IssuedTokens:
    user = await session.scalar(select(User).where(User.email == email))
    if user is None or not verify_password(password, user.password_hash):
        raise InvalidCredentialsError(email)
    return await _issue_tokens_for(session, user)


async def refresh_access_token(
    session: AsyncSession, raw_refresh_token: str
) -> RefreshedAccessToken:
    token_hash = hash_refresh_token(raw_refresh_token)
    stored = await session.scalar(select(RefreshToken).where(RefreshToken.token_hash == token_hash))

    if stored is None or stored.revoked_at is not None:
        raise InvalidRefreshTokenError("refresh token not found or revoked")

    if stored.expires_at <= datetime.now(UTC):
        raise InvalidRefreshTokenError("refresh token expired")

    access_token, expires_in = create_access_token(stored.user_id)
    return RefreshedAccessToken(access_token=access_token, expires_in=expires_in)
