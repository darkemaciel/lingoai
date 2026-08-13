"""Password hashing + JWT access/refresh token issuance and validation.

Per research.md §10: email/password hashed with bcrypt, a short-lived JWT
access token (~15 min) plus a longer-lived opaque refresh token (~30 days).
The access token is a signed JWT (self-contained, not looked up in the DB);
the refresh token is a random opaque string whose SHA-256 hash is persisted
server-side (``identity.infrastructure.models.RefreshToken``) so it can be
revoked/rotated without needing JWT blocklisting.

**Uses the ``bcrypt`` library directly, not passlib's ``CryptContext``.**
passlib 1.7.4 (last released 2020, unmaintained) probes the ``bcrypt``
package for a `__about__.__version__` attribute that bcrypt >=4.1 no longer
exposes, which makes passlib's backend auto-detection crash outright on any
current bcrypt install. Calling ``bcrypt.hashpw``/``checkpw`` directly
sidesteps that broken detection shim entirely.

Env vars (see .env.example): ``JWT_SECRET_KEY``,
``JWT_ACCESS_TOKEN_EXPIRE_MINUTES``, ``JWT_REFRESH_TOKEN_EXPIRE_DAYS``.
"""

from __future__ import annotations

import hashlib
import os
import secrets
import uuid
from datetime import UTC, datetime, timedelta

import bcrypt
from jose import JWTError, jwt

_JWT_ALGORITHM = "HS256"
_ACCESS_TOKEN_TYPE = "access"

# bcrypt's underlying algorithm silently ignores password bytes beyond this
# length; modern bcrypt (>=4.1) raises instead of silently truncating, so
# request models (identity/api/routes.py) cap `password` at this length to
# turn that into an ordinary 422 validation error rather than a 500.
MAX_PASSWORD_BYTES = 72


class InvalidTokenError(Exception):
    """Raised when an access token is missing, malformed, expired, or not
    actually an access token (e.g. someone passes a refresh token)."""


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))


def _access_token_ttl() -> timedelta:
    minutes = int(os.environ.get("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "15"))
    return timedelta(minutes=minutes)


def refresh_token_ttl() -> timedelta:
    days = int(os.environ.get("JWT_REFRESH_TOKEN_EXPIRE_DAYS", "30"))
    return timedelta(days=days)


def _secret_key() -> str:
    # A hardcoded fallback would violate NFR-3 in production, but importing
    # this module must not crash a dev/test run that has no .env loaded yet
    # (e.g. `alembic` invocations, unit tests). Callers that issue/verify
    # real tokens outside local dev MUST set JWT_SECRET_KEY (see .env.example).
    return os.environ.get("JWT_SECRET_KEY", "insecure-dev-secret-change-me")


def create_access_token(user_id: uuid.UUID) -> tuple[str, int]:
    """Issue a signed JWT access token for ``user_id``.

    Returns ``(token, expires_in_seconds)`` — ``expires_in`` matches the
    `POST /api/v1/auth/login` / `/refresh` response shape in
    contracts/rest-api.md.
    """
    ttl = _access_token_ttl()
    expire_at = datetime.now(UTC) + ttl
    payload = {"sub": str(user_id), "type": _ACCESS_TOKEN_TYPE, "exp": expire_at}
    token = jwt.encode(payload, _secret_key(), algorithm=_JWT_ALGORITHM)
    return token, int(ttl.total_seconds())


def decode_access_token(token: str) -> uuid.UUID:
    """Validate ``token`` and return the ``user_id`` it was issued for.

    Raises ``InvalidTokenError`` if the token is malformed, expired, signed
    with a different key, or not an access token.
    """
    try:
        payload = jwt.decode(token, _secret_key(), algorithms=[_JWT_ALGORITHM])
    except JWTError as exc:
        raise InvalidTokenError("invalid or expired access token") from exc
    if payload.get("type") != _ACCESS_TOKEN_TYPE:
        raise InvalidTokenError("token is not an access token")
    subject = payload.get("sub")
    if not subject:
        raise InvalidTokenError("access token missing subject")
    try:
        return uuid.UUID(subject)
    except ValueError as exc:
        raise InvalidTokenError("access token subject is not a valid user id") from exc


def generate_refresh_token() -> tuple[str, str, datetime]:
    """Generate a new opaque refresh token.

    Returns ``(raw_token, token_hash, expires_at)``. Only ``token_hash``
    (SHA-256 hex digest) is ever persisted — ``raw_token`` is returned to
    the caller once, to hand back to the client, and never stored.
    """
    raw_token = secrets.token_urlsafe(48)
    token_hash = hash_refresh_token(raw_token)
    expires_at = datetime.now(UTC) + refresh_token_ttl()
    return raw_token, token_hash, expires_at


def hash_refresh_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
