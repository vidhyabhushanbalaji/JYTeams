"""Request authentication.

Two modes, chosen with ``AUTH_MODE``:

* ``dev`` (default) — trust the ``X-Dev-User-Id`` header so the API can be exercised
  before a Supabase project exists. It is logged loudly at startup because it must
  never face the internet.
* ``supabase`` — verify the bearer token with Supabase Auth and return that user.

Section endpoints depend on :func:`get_current_user`; they never parse headers
themselves.
"""

from __future__ import annotations

import logging
from functools import lru_cache
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel
from starlette.concurrency import run_in_threadpool

from app.core.config import get_settings

logger = logging.getLogger(__name__)

_bearer = HTTPBearer(auto_error=False)


class CurrentUser(BaseModel):
    """The authenticated caller."""

    id: str
    email: str | None = None


@lru_cache(maxsize=1)
def _warn_about_dev_auth() -> None:
    logger.warning(
        "AUTH_MODE=dev: bearer tokens are ignored and the X-Dev-User-Id header is "
        "trusted. Set AUTH_MODE=supabase before exposing this API."
    )


async def _verify_supabase_token(token: str) -> CurrentUser:
    from app.db.supabase import admin_client

    client = admin_client()
    try:
        response = await run_in_threadpool(lambda: client.auth.get_user(token))
    except Exception as exc:  # noqa: BLE001 - normalised into a 401 below
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    user = getattr(response, "user", None)
    if user is None or not getattr(user, "id", None):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return CurrentUser(id=str(user.id), email=getattr(user, "email", None))


async def get_current_user(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)] = None,
) -> CurrentUser:
    """Resolve the caller, or raise 401."""
    settings = get_settings()

    if settings.auth_mode == "dev":
        _warn_about_dev_auth()
        return CurrentUser(
            id=request.headers.get("X-Dev-User-Id", settings.dev_user_id),
            email=request.headers.get("X-Dev-User-Email"),
        )

    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return await _verify_supabase_token(credentials.credentials)
