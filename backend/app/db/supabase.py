"""Supabase client factories and a health probe.

The service-role key stays server-side: it bypasses row level security, so it must never
be sent to the Electron client. ``anon_client()`` is available for the cases where the
request's own JWT should be honoured instead.

Both clients share one ``httpx.Client`` with **HTTP/2 turned off**. storage3 builds its own
client with ``http2=True``, and httpcore's sync HTTP/2 read path raises ``WinError 10035`` ("a
non-blocking socket operation could not be completed immediately") on Windows when Graph
Creation uploads several objects at once — one such blip fails a whole job. HTTP/1.1 over a
single connection pool is supported, thread-safe and fast enough for a handful of markdown
files.
"""

from __future__ import annotations

import logging
from functools import lru_cache

import httpx
from fastapi import HTTPException, status
from supabase import Client, ClientOptions, create_client

from app.core.config import get_settings

logger = logging.getLogger(__name__)

_HEALTH_TIMEOUT_SECONDS = 5.0
#: Shared timeout for the sync client. Storage uploads are the slow part, so read/write get a
#: generous budget: httpx's 5 s default would start failing larger documents.
_SUPABASE_TIMEOUT = httpx.Timeout(connect=10.0, read=60.0, write=60.0, pool=10.0)


def build_http_client() -> httpx.Client:
    """The sync client every Supabase sub-client shares (PostgREST, auth and storage)."""
    return httpx.Client(
        http2=False,
        # storage3 enables redirects on its own client; keep that so downloads still work.
        follow_redirects=True,
        timeout=_SUPABASE_TIMEOUT,
        limits=httpx.Limits(max_connections=20, max_keepalive_connections=10),
    )


@lru_cache(maxsize=2)
def _cached_client(url: str, key: str) -> Client:
    return create_client(url, key, ClientOptions(httpx_client=build_http_client()))


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
