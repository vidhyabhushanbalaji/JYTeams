"""The whole Graph Add journey over HTTP, against a tree that already has content.

The other test modules check one collaborator each. This one drives the routes exactly as
the wizard does — suggest, choose, place — and asserts the tree afterwards, so a regression
in the interaction between the walk, the writes and the description refresh shows up here.

The first test uses the real ``MockNavigator`` on a realistic tree, which is the only place
the semantic walk is exercised end to end; the rest script the navigator so the assertions
stay exact.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.graph_add.llm import MockNavigator
from app.graph_add.navigate import Navigator
from app.graph_add.router import get_service
from app.graph_add.service import GraphAddService
from app.graph_add.tests.fakes import (
    InMemoryAddRepository,
    InMemoryObjectStore,
    ScriptedNavigator,
)
from app.main import create_app

Row = dict[str, Any]

SUGGEST = "/api/graph-add/suggestions"
PLACE = "/api/graph-add/placements"

SESSION_DOC = b"# Session expiry\n\nHow sessions expire and how the token refresh flow works."
TOKENS_DOC = b"# Tokens\n\nHow authentication tokens are refreshed."

#: The published contract, pinned so a rename or a dropped field fails loudly.
SUGGESTION_KEYS = {
    "rank",
    "score",
    "directory_id",
    "path",
    "name",
    "depth",
    "description",
    "direct_file_count",
    "child_directory_count",
    "is_leaf",
    "reason",
    "proposed_new_directory_names",
    "name_available",
    "suggested_file_names",
    "identical_content_at",
}
SUGGESTION_RESPONSE_KEYS = {
    "request_id",
    "project_id",
    "status",
    "expires_at",
    "file",
    "suggestions",
    "traversal",
}
FILE_BRIEF_KEYS = {"name", "size_bytes", "content_sha256", "summary"}
TRAVERSAL_KEYS = {"expanded", "visited", "degraded", "budget_exhausted", "model"}
PLACEMENT_KEYS = {
    "project_id",
    "request_id",
    "directory_id",
    "directory_path",
    "created_directory",
    "refreshed_directories",
    "file",
}


def _client(repository: InMemoryAddRepository, navigator: Navigator | None = None) -> TestClient:
    """A TestClient wired to the in-memory repository and the given navigator."""
    service = GraphAddService(
        repository=repository,
        store=InMemoryObjectStore(),
        navigator=navigator or _walking(),
        settings=get_settings(),
    )
    application = create_app()
    application.dependency_overrides[get_service] = lambda: service
    return TestClient(application)


def _walking() -> ScriptedNavigator:
    """A navigator that resolves straight to ``docs/auth``."""
    return ScriptedNavigator(matches={"": [("docs", 0.9)], "docs": [("auth", 0.9)]})


def _suggest(
    client: TestClient,
    project_id: str,
    *,
    filename: str = "session-expiry.md",
    data: bytes = SESSION_DOC,
):
    return client.post(
        SUGGEST,
        data={"project_id": project_id},
        files={"file": (filename, data, "text/markdown")},
    )


def _place(client: TestClient, request_id: str, directory_id: str, **extra: Any):
    return client.post(
        PLACE, json={"request_id": request_id, "directory_id": directory_id, **extra}
    )


def _directories(repository: InMemoryAddRepository, project_id: str) -> dict[str, Row]:
    rows = repository.directories.values()
    return {row["path"]: row for row in rows if row["project_id"] == project_id}


def _files(repository: InMemoryAddRepository, project_id: str) -> dict[str, Row]:
    rows = repository.files.values()
    return {row["path"]: row for row in rows if row["project_id"] == project_id}


def _snapshot(repository: InMemoryAddRepository, project_id: str) -> tuple[int, int]:
    return len(_directories(repository, project_id)), len(_files(repository, project_id))


@pytest.fixture()
def repository() -> InMemoryAddRepository:
    return InMemoryAddRepository()


@pytest.fixture()
def tree(repository: InMemoryAddRepository) -> SimpleNamespace:
    """``root → docs → {guides, api, auth}`` with files already in place."""
    project = repository.seed_project(owner_id="user-1")
    root_id = project["root_directory_id"]
    repository.seed_file(
        project["id"], directory_id=root_id, name="README.md", summary="Project overview."
    )
    docs = repository.seed_directory(
        project["id"],
        parent_id=root_id,
        name="docs",
        description=(
            "Team guides and how-to articles, including authentication, session handling "
            "and the HTTP API reference."
        ),
    )
    guides = repository.seed_directory(
        project["id"],
        parent_id=docs["id"],
        name="guides",
        description="Step-by-step how-to articles.",
    )
    api = repository.seed_directory(
        project["id"],
        parent_id=docs["id"],
        name="api",
        description="HTTP endpoint reference and payloads.",
    )
    auth = repository.seed_directory(
        project["id"],
        parent_id=docs["id"],
        name="auth",
        description="Authentication and authorization: tokens, sessions, sign-in flows.",
    )
    repository.seed_file(
        project["id"], directory_id=guides["id"], name="release.md", summary="Release checklist."
    )
    repository.seed_file(
        project["id"], directory_id=api["id"], name="users.md", summary="User endpoints."
    )
    repository.seed_file(
        project["id"], directory_id=api["id"], name="errors.md", summary="Error codes."
    )
    repository.seed_file(
        project["id"],
        directory_id=auth["id"],
        name="tokens.md",
        summary="Token refresh and expiry.",
    )
    return SimpleNamespace(
        project=project,
        root_id=root_id,
        docs=docs,
        guides=guides,
        api=api,
        auth=auth,
    )


def test_suggestion_walks_into_the_matching_branch(
    repository: InMemoryAddRepository, tree: SimpleNamespace
) -> None:
    with _client(repository, MockNavigator()) as client:
        response = _suggest(client, tree.project["id"])

    assert response.status_code == 200
    body = response.json()

    assert set(body) == SUGGESTION_RESPONSE_KEYS
    assert set(body["file"]) == FILE_BRIEF_KEYS
    assert set(body["traversal"]) == TRAVERSAL_KEYS
    assert all(set(item) == SUGGESTION_KEYS for item in body["suggestions"])

    paths = [item["path"] for item in body["suggestions"]]
    assert paths[0] == "docs/auth", "the walk should descend root → docs → auth"
    assert paths[-1] == "", "the project root is always offered last"

    top = body["suggestions"][0]
    assert [item["rank"] for item in body["suggestions"]] == list(range(1, len(paths) + 1))
    assert top["directory_id"] == tree.auth["id"]
    assert top["is_leaf"] is True
    assert top["direct_file_count"] == 1
    assert top["reason"]
    assert top["proposed_new_directory_names"]
    assert top["name_available"] is True
    assert top["identical_content_at"] == []

    assert body["traversal"]["model"] == "mock"
    assert body["traversal"]["expanded"] >= 2
    assert body["traversal"]["degraded"] is False
    assert body["status"] == "suggested"
    assert body["expires_at"]


def test_place_direct_adds_the_file_to_the_chosen_folder(
    repository: InMemoryAddRepository, tree: SimpleNamespace
) -> None:
    with _client(repository) as client:
        suggestion = _suggest(client, tree.project["id"]).json()
        response = _place(
            client, suggestion["request_id"], suggestion["suggestions"][0]["directory_id"]
        )

    assert response.status_code == 201
    body = response.json()
    assert set(body) == PLACEMENT_KEYS
    assert body["created_directory"] is False
    assert body["directory_path"] == "docs/auth"
    assert body["file"]["path"] == "docs/auth/session-expiry.md"
    assert body["file"]["summary_status"] == "ok"
    assert body["refreshed_directories"] == 3  # docs/auth, docs, root

    directories = _directories(repository, tree.project["id"])
    assert directories["docs/auth"]["direct_file_count"] == 2
    assert "session-expiry.md" in directories["docs/auth"]["description"]
    assert "auth" in directories["docs"]["description"]
    assert "docs" in directories[""]["description"]

    # The rest of the tree is untouched.
    assert directories["docs/api"]["direct_file_count"] == 2
    assert directories["docs/guides"]["direct_file_count"] == 1

    project_row = repository.projects[tree.project["id"]]
    assert project_row["description"] == directories[""]["description"]
    assert repository.requests[suggestion["request_id"]]["status"] == "placed"


def test_place_creates_a_new_folder_under_the_chosen_one(
    repository: InMemoryAddRepository, tree: SimpleNamespace
) -> None:
    with _client(repository) as client:
        suggestion = _suggest(client, tree.project["id"]).json()
        response = _place(
            client,
            suggestion["request_id"],
            tree.auth["id"],
            placement="new_directory",
            new_directory_name="session handling",
        )

    assert response.status_code == 201
    body = response.json()
    assert body["created_directory"] is True
    assert body["directory_path"] == "docs/auth/session handling"
    assert body["file"]["path"] == "docs/auth/session handling/session-expiry.md"

    directories = _directories(repository, tree.project["id"])
    created = directories["docs/auth/session handling"]
    assert created["depth"] == 3
    assert created["ltree_path"] == "docs.auth.session_handling"
    assert created["direct_file_count"] == 1
    assert created["child_directory_count"] == 0
    assert "session-expiry.md" in created["description"]

    # The chosen folder now has a subfolder, and its description says so.
    assert directories["docs/auth"]["child_directory_count"] == 1
    assert directories["docs/auth"]["direct_file_count"] == 1
    assert "session handling" in directories["docs/auth"]["description"]


def test_a_name_clash_is_reported_and_resolved_by_renaming(
    repository: InMemoryAddRepository, tree: SimpleNamespace
) -> None:
    with _client(repository) as client:
        suggestion = _suggest(
            client, tree.project["id"], filename="tokens.md", data=TOKENS_DOC
        ).json()

        top = suggestion["suggestions"][0]
        assert top["path"] == "docs/auth"
        assert top["name_available"] is False
        assert top["suggested_file_names"][0] == "tokens-2.md"

        conflict = _place(client, suggestion["request_id"], tree.auth["id"])
        assert conflict.status_code == 409
        detail = conflict.json()["detail"]
        assert detail["conflict"]["path"] == "docs/auth/tokens.md"
        assert detail["conflict"]["identical_content"] is False
        assert detail["suggested_names"][0] == "tokens-2.md"

        # The request is not consumed by a rejection, so the rename can be committed.
        renamed = _place(client, suggestion["request_id"], tree.auth["id"], file_name="tokens-2.md")

    assert renamed.status_code == 201
    assert renamed.json()["file"]["path"] == "docs/auth/tokens-2.md"


def test_identical_content_elsewhere_is_allowed(
    repository: InMemoryAddRepository, tree: SimpleNamespace
) -> None:
    with _client(repository) as client:
        first = _suggest(client, tree.project["id"]).json()
        assert _place(client, first["request_id"], tree.auth["id"]).status_code == 201

        second = _suggest(client, tree.project["id"]).json()
        assert second["suggestions"][0]["identical_content_at"] == ["docs/auth/session-expiry.md"]

        response = _place(client, second["request_id"], tree.docs["id"])

    assert response.status_code == 201
    assert response.json()["file"]["path"] == "docs/session-expiry.md"

    files = _files(repository, tree.project["id"])
    here = files["docs/auth/session-expiry.md"]
    there = files["docs/session-expiry.md"]
    assert here["content_sha256"] == there["content_sha256"]
    assert here["storage_path"] == there["storage_path"], "one blob serves both paths"


def test_a_second_placement_with_the_same_request_is_rejected(
    repository: InMemoryAddRepository, tree: SimpleNamespace
) -> None:
    with _client(repository) as client:
        suggestion = _suggest(client, tree.project["id"]).json()
        first = _place(client, suggestion["request_id"], tree.auth["id"])
        assert first.status_code == 201

        again = _place(client, suggestion["request_id"], tree.auth["id"])

    assert again.status_code == 409
    detail = again.json()["detail"]
    assert detail["status"] == "placed"
    assert detail["file_id"] == first.json()["file"]["id"]
    assert len(_files(repository, tree.project["id"])) == 6  # 5 seeded + 1 placed


def test_a_foreign_project_and_an_expired_request_are_refused(
    repository: InMemoryAddRepository, tree: SimpleNamespace
) -> None:
    foreign = repository.seed_project(owner_id="someone-else")

    with _client(repository) as client:
        assert _suggest(client, foreign["id"]).status_code == 404

        suggestion = _suggest(client, tree.project["id"]).json()
        repository.requests[suggestion["request_id"]]["expires_at"] = (
            datetime.now(UTC) - timedelta(minutes=1)
        ).isoformat()
        response = _place(client, suggestion["request_id"], tree.auth["id"])

    assert response.status_code == 410
    assert "expired" in response.json()["detail"]
    assert repository.requests[suggestion["request_id"]]["status"] == "expired"


def test_a_rejected_placement_leaves_the_tree_unchanged(
    repository: InMemoryAddRepository, tree: SimpleNamespace
) -> None:
    repository.seed_directory(tree.project["id"], parent_id=tree.auth["id"], name="sessions")
    before = _snapshot(repository, tree.project["id"])

    with _client(repository) as client:
        suggestion = _suggest(client, tree.project["id"]).json()
        response = _place(
            client,
            suggestion["request_id"],
            tree.auth["id"],
            placement="new_directory",
            new_directory_name="sessions",
        )

    assert response.status_code == 409
    assert response.json()["detail"]["suggested_names"][0] == "sessions-2"
    assert _snapshot(repository, tree.project["id"]) == before
