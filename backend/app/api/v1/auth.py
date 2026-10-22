"""Cookie-session authentication endpoints and authorization dependencies."""

from __future__ import annotations

import hashlib
import hmac
import secrets
import threading
import time
from collections import deque
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Literal, cast
from urllib.parse import urlsplit
from uuid import UUID, uuid4

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.orm import Session as OrmSession

from app.core.config import AppSettings, get_settings
from app.db.models import Session, User
from app.db.session import get_db
from app.services.audit import record_security_event

router = APIRouter(prefix="/auth", tags=["authentication"])
COOKIE_NAME = "safecity_session"
_password_hasher = PasswordHasher()
_dummy_password_hash = _password_hasher.hash(secrets.token_urlsafe(32))
_process_csrf_secret = secrets.token_bytes(32)


class LoginRequest(BaseModel):
    email: EmailStr = Field(max_length=320)
    password: str = Field(min_length=1, max_length=1024)


class UserProfile(BaseModel):
    id: UUID
    display_name: str
    email: EmailStr
    role: Literal["operator", "supervisor", "technical_admin"]
    is_active: bool


class LoginResponse(BaseModel):
    user: UserProfile


class CsrfResponse(BaseModel):
    csrf_token: str


class LoginRateLimiter:
    """Single-process account-and-IP aware limiter for the documented MVP deployment."""

    def __init__(self, limit: int = 10, window_seconds: int = 60, max_keys: int = 10_000) -> None:
        self.limit = limit
        self.window_seconds = window_seconds
        self.max_keys = max_keys
        self._attempts: dict[str, deque[float]] = {}
        self._lock = threading.Lock()

    def check(self, key: str) -> int | None:
        now = time.monotonic()
        with self._lock:
            attempts = self._attempts.get(key)
            if attempts is None:
                if len(self._attempts) >= self.max_keys:
                    oldest_key = min(
                        self._attempts,
                        key=lambda item: self._attempts[item][-1] if self._attempts[item] else 0,
                    )
                    del self._attempts[oldest_key]
                attempts = deque()
                self._attempts[key] = attempts
            while attempts and now - attempts[0] >= self.window_seconds:
                attempts.popleft()
            if len(attempts) >= self.limit:
                return max(1, self.window_seconds - int(now - attempts[0]))
            attempts.append(now)
            return None

    def clear(self, key: str) -> None:
        with self._lock:
            self._attempts.pop(key, None)


login_limiter = LoginRateLimiter()
login_ip_limiter = LoginRateLimiter(limit=30)


@dataclass(frozen=True)
class AuthContext:
    user: User
    session: Session
    token: str


def _problem(
    request: Request,
    status: int,
    code: str,
    title: str,
    detail: str,
    *,
    retry_after: int | None = None,
) -> JSONResponse:
    request_id = getattr(request.state, "request_id", None) or str(uuid4())
    headers = {"Retry-After": str(retry_after)} if retry_after is not None else None
    return JSONResponse(
        {
            "type": f"https://example.invalid/problems/{code.lower()}",
            "title": title,
            "status": status,
            "detail": detail,
            "instance": request.url.path,
            "code": code,
            "request_id": request_id,
        },
        status_code=status,
        headers=headers,
    )


def _csrf_secret(settings: AppSettings) -> bytes:
    if settings.session_csrf_secret is not None:
        return settings.session_csrf_secret.get_secret_value().encode()
    return _process_csrf_secret


def _csrf_token(context: AuthContext, settings: AppSettings) -> str:
    return hmac.new(
        _csrf_secret(settings), context.session.token_hash.encode(), hashlib.sha256
    ).hexdigest()


def _as_utc(value: datetime | None) -> datetime | None:
    if value is not None and value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value


def _origin_is_allowed(request: Request, settings: AppSettings) -> bool:
    origin = request.headers.get("origin")
    if origin is None:
        referer = request.headers.get("referer")
        if referer is None:
            return False
        parsed = urlsplit(referer)
        origin = f"{parsed.scheme}://{parsed.netloc}"
    configured = {settings.public_app_origin, *settings.csrf_allowed_origins}
    return origin in configured


def get_auth_context(
    request: Request,
    db: OrmSession = Depends(get_db),
    settings: AppSettings = Depends(get_settings),
) -> AuthContext:
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        raise HTTPException(status_code=401, detail="AUTHENTICATION_REQUIRED")
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    row = db.execute(
        select(Session, User)
        .join(User, User.id == Session.user_id)
        .where(Session.token_hash == token_hash)
    ).first()
    now = datetime.now(UTC)
    if row is None:
        raise HTTPException(status_code=401, detail="AUTHENTICATION_REQUIRED")
    session, user = row
    idle_cutoff = now - timedelta(seconds=settings.session_idle_ttl_seconds)
    expires_at = _as_utc(session.expires_at)
    last_seen_at = _as_utc(session.last_seen_at)
    if (
        session.revoked_at is not None
        or expires_at is None
        or expires_at <= now
        or (last_seen_at is not None and last_seen_at <= idle_cutoff)
        or not user.is_active
    ):
        if session.revoked_at is None:
            session.revoked_at = now
            db.commit()
        raise HTTPException(status_code=401, detail="AUTHENTICATION_REQUIRED")
    session.last_seen_at = now
    db.commit()
    return AuthContext(user, session, token)


def require_csrf(
    request: Request,
    context: AuthContext = Depends(get_auth_context),
    settings: AppSettings = Depends(get_settings),
) -> AuthContext:
    supplied = request.headers.get("x-csrf-token", "")
    expected = _csrf_token(context, settings)
    if not _origin_is_allowed(request, settings) or not hmac.compare_digest(supplied, expected):
        raise HTTPException(status_code=403, detail="PERMISSION_DENIED")
    return context


def require_roles(*roles: str):
    """Build a server-side role dependency for protected operation routes."""

    def check(context: AuthContext = Depends(get_auth_context)) -> AuthContext:
        if context.user.role not in roles:
            raise HTTPException(status_code=403, detail="PERMISSION_DENIED")
        return context

    return check


@router.post("/login", response_model=LoginResponse)
def login(
    body: LoginRequest,
    request: Request,
    response: Response,
    db: OrmSession = Depends(get_db),
    settings: AppSettings = Depends(get_settings),
) -> LoginResponse | JSONResponse:
    client_ip = request.client.host if request.client is not None else "unknown"
    normalized_email = str(body.email).strip().lower()
    account_key = hashlib.sha256(normalized_email.encode()).hexdigest()
    ip_key = hashlib.sha256(client_ip.encode()).hexdigest()
    retry_after = (
        max(
            (
                value
                for value in (login_limiter.check(account_key), login_ip_limiter.check(ip_key))
                if value
            ),
            default=0,
        )
        or None
    )
    if retry_after is not None:
        record_security_event(db, request, action="auth.login", result="denied")
        db.commit()
        return _problem(
            request,
            429,
            "RATE_LIMIT_EXCEEDED",
            "Too many attempts",
            "Wait before trying again.",
            retry_after=retry_after,
        )
    if request.headers.get("origin") and not _origin_is_allowed(request, settings):
        record_security_event(db, request, action="auth.login", result="denied")
        db.commit()
        return _problem(
            request,
            403,
            "PERMISSION_DENIED",
            "Request origin denied",
            "This request origin is not permitted.",
        )

    user = db.scalar(select(User).where(User.email == normalized_email))
    stored_hash = user.password_hash if user is not None else _dummy_password_hash
    valid_password: bool
    try:
        valid_password = _password_hasher.verify(stored_hash, body.password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        valid_password = False
    if user is None or not user.is_active or not valid_password:
        record_security_event(db, request, action="auth.login", result="denied")
        db.commit()
        return _problem(
            request,
            401,
            "AUTHENTICATION_REQUIRED",
            "Sign-in failed",
            "Email or password is incorrect.",
        )

    login_limiter.clear(account_key)
    login_ip_limiter.clear(ip_key)
    token = secrets.token_urlsafe(32)
    now = datetime.now(UTC)
    session = Session(
        user_id=user.id,
        token_hash=hashlib.sha256(token.encode()).hexdigest(),
        created_at=now,
        expires_at=now + timedelta(seconds=settings.session_ttl_seconds),
    )
    db.add(session)
    record_security_event(db, request, action="auth.login", result="success", actor=user)
    db.commit()
    response.set_cookie(
        COOKIE_NAME,
        token,
        max_age=settings.session_ttl_seconds,
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        path=settings.api_prefix,
    )
    return LoginResponse(
        user=UserProfile(
            id=user.id,
            display_name=user.display_name,
            email=user.email,
            role=cast(Literal["operator", "supervisor", "technical_admin"], user.role),
            is_active=user.is_active,
        )
    )


@router.get("/me", response_model=UserProfile)
def current_user(context: AuthContext = Depends(get_auth_context)) -> UserProfile:
    user = context.user
    return UserProfile(
        id=user.id,
        display_name=user.display_name,
        email=user.email,
        role=cast(Literal["operator", "supervisor", "technical_admin"], user.role),
        is_active=user.is_active,
    )


@router.get("/csrf", response_model=CsrfResponse)
def csrf_token(
    context: AuthContext = Depends(get_auth_context),
    settings: AppSettings = Depends(get_settings),
) -> CsrfResponse:
    return CsrfResponse(csrf_token=_csrf_token(context, settings))


@router.post("/logout", status_code=204)
def logout(
    request: Request,
    response: Response,
    context: AuthContext = Depends(require_csrf),
    settings: AppSettings = Depends(get_settings),
    db: OrmSession = Depends(get_db),
) -> Response:
    context.session.revoked_at = datetime.now(UTC)
    record_security_event(db, request, action="auth.logout", result="success", actor=context.user)
    db.commit()
    response.delete_cookie(
        COOKIE_NAME,
        path=settings.api_prefix,
        secure=settings.cookie_secure,
        httponly=True,
        samesite=settings.cookie_samesite,
    )
    response.status_code = 204
    return response
