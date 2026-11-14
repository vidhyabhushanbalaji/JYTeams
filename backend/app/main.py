"""FastAPI application factory for the JYTeams backend.

Composition only: configuration, CORS, the health router and the three section routers.
Section behaviour lives in ``app/<section>/``; nothing here designs it.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.routing import APIRouter

from app import __version__
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.graph_add.router import router as graph_add_router
from app.graph_ai_search.router import router as graph_ai_search_router
from app.graph_creation.router import router as graph_creation_router
from app.health.router import router as health_router

API_TITLE = "JYTeams API"

#: (URL slug, router) pairs. Each router is owned by exactly one section.
SECTION_ROUTERS: tuple[tuple[str, APIRouter], ...] = (
    ("graph-creation", graph_creation_router),
    ("graph-add", graph_add_router),
    ("graph-ai-search", graph_ai_search_router),
)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Configure logging for the app's lifetime."""
    configure_logging(get_settings().log_level)
    yield


def create_app() -> FastAPI:
    """Build the application (factory, so tests get a clean instance)."""
    settings = get_settings()
    application = FastAPI(
        title=API_TITLE,
        version=__version__,
        summary="Makes Microsoft Teams project information easier to reach.",
        lifespan=lifespan,
    )

    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    application.include_router(health_router)
    for slug, section_router in SECTION_ROUTERS:
        application.include_router(section_router, prefix=f"{settings.api_prefix}/{slug}")

    @application.get("/", tags=["Meta"], summary="API root")
    async def root() -> dict[str, str]:
        return {
            "name": API_TITLE,
            "version": __version__,
            "docs": "/docs",
            "health": "/health",
        }

    return application


app = create_app()


def create_app() -> FastAPI:
    """Build the application (factory, so tests get a clean instance)."""
    settings = get_settings()
    application = FastAPI(
        title=API_TITLE,
        version=__version__,
        summary="Makes Microsoft Teams project information easier to reach.",
        lifespan=lifespan,
    )

    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    application.include_router(health_router)
    for slug, section_router in SECTION_ROUTERS:
        application.include_router(section_router, prefix=f"{settings.api_prefix}/{slug}")

    @application.get("/", tags=["Meta"], summary="API root")
    async def root() -> dict[str, str]:
        return {
            "name": API_TITLE,
            "version": __version__,
            "docs": "/docs",
            "health": "/health",
        }

    return application


app = create_app()
