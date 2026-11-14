"""Health endpoints.

``/health`` is a pure liveness probe. The other probe reports 503 with a readable reason
when its service is unconfigured or unreachable, which is the quickest way to confirm
the credentials in ``backend/.env`` actually work.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, status

from app.db import supabase

router = APIRouter(tags=["Health"])


@router.get("/health", summary="Liveness probe")
async def health() -> dict[str, str]:
    """Always answers 200 while the process is serving requests."""
    return {"status": "ok"}


@router.get("/health/supabase", summary="Supabase connectivity probe")
async def health_supabase() -> dict[str, Any]:
    ok, detail = await supabase.ping()
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Supabase unavailable: {detail}",
        )
    return {"status": "ok", "service": "supabase", "detail": detail}
