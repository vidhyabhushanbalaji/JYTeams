"""Supabase client factories and a health probe.

The service-role key stays server-side: it bypasses row level security, so it must never
be sent to the Electron client. ``anon_client()`` is available for the cases where the
request's own JWT should be honoured instead.
"""

from __future__ import annotations

import logging
from functools import lru_cache

import httpx
from fastapi import HTTPException, status
from supabase import Client, create_client

from app.core.config import get_settings

logger = logging.getLogger(__name__)

_HEALTH_TIMEOUT_SECONDS = 5.0


@lru_cache(maxsize=2)
def _cached_client(url: str, key: str) -> Client:
    return create_client(url, key)


def admin_client() -> Client:
    """Service-role client (full database access). Server-side use only."""
    settings = get_settings()
    if not settings.supabase_configured:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "Supabase is not configured. Set SUPABASE_URL and "
                "SUPABASE_SERVICE_ROLE_KEY in backend/.env and restart the API."
            ),
        )
    return _cached_client(settings.supabase_url, settings.supabase_service_role_key)


def anon_client() -> Client:
    """Anon-key client: subject to row level security, like the Electron app."""
    settings = get_settings()
    if not (settings.supabase_url and settings.supabase_anon_key):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "Supabase anon access is not configured. Set SUPABASE_URL and "
                "SUPABASE_ANON_KEY in backend/.env and restart the API."
            ),
        )
    return _cached_client(settings.supabase_url, settings.supabase_anon_key)


async def ping() -> tuple[bool, str]:
    """Check that the Supabase project is reachable. Returns ``(ok, detail)``."""
    settings = get_settings()
    if not settings.supabase_url:
        return False, "Supabase is not configured (SUPABASE_URL)"

    url = f"{settings.supabase_url.rstrip('/')}/auth/v1/health"
    headers = {"apikey": settings.supabase_anon_key} if settings.supabase_anon_key else {}
    try:
        async with httpx.AsyncClient(timeout=_HEALTH_TIMEOUT_SECONDS) as client:
            response = await client.get(url, headers=headers)
    except httpx.HTTPError as exc:
        return False, f"{type(exc).__name__}: {exc}"

    if response.status_code >= 400:
        return False, f"unexpected HTTP {response.status_code} from {url}"
    return True, f"reachable (HTTP {response.status_code})"
