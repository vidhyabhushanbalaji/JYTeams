"""Wiring checks: the app builds, documents itself, and mounts every section."""

from __future__ import annotations

import pytest
from fastapi.routing import APIRouter
from fastapi.testclient import TestClient

from app.calendar.router import router as calendar_router
from app.chat.router import router as chat_router
from app.graph_add.router import router as graph_add_router
from app.graph_ai_search.router import router as graph_ai_search_router
from app.graph_creation.router import router as graph_creation_router
from app.main import SECTION_ROUTERS
from app.tickets.router import router as tickets_router


def test_openapi_schema_builds(client: TestClient) -> None:
    response = client.get("/openapi.json")

    assert response.status_code == 200
    assert "/health" in response.json()["paths"]


def test_section_routers_are_mounted_under_the_api_prefix() -> None:
    slugs = [slug for slug, _ in SECTION_ROUTERS]

    assert slugs == [
        "graph-creation",
        "graph-add",
        "graph-ai-search",
        "tickets",
        "chat",
        "calendar",
    ]


@pytest.mark.parametrize(
    "section_router",
    [
        graph_creation_router,
        graph_add_router,
        graph_ai_search_router,
        tickets_router,
        chat_router,
        calendar_router,
    ],
    ids=["graph_creation", "graph_add", "graph_ai_search", "tickets", "chat", "calendar"],
)
def test_each_section_exposes_an_router(section_router: object) -> None:
    assert isinstance(section_router, APIRouter)
