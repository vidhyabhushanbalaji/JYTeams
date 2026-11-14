"""Behaviour of the suggest → place flow against in-memory collaborators."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from fastapi import HTTPException

from app.core.config import get_settings
from app.graph_add.schemas import PlacementMode
from app.graph_add.service import GraphAddService
from app.graph_add.storage import content_hash
from app.graph_add.tests.fakes import (
    InMemoryAddRepository,
    InMemoryObjectStore,
    ScriptedNavigator,
)

DOC = b"# Auth\n\nToken refresh and session expiry."


def _service(navigator: ScriptedNavigator | None = None):
    repository = InMemoryAddRepository()
    store = InMemoryObjectStore()
    service = GraphAddService(
        repository=repository,
        store=store,
        navigator=navigator or ScriptedNavigator(),
        settings=get_settings(),
    )
    return service, repository, store


def _seed(repository: InMemoryAddRepository):
    """``root → docs → docs/api``, with one file already in ``docs/api``."""
    project = repository.seed_project()
    root_id = project["root_directory_id"]
    docs = repository.seed_directory(
        project["id"], parent_id=root_id, name="docs", description="Guides and how-tos."
    )
    api = repository.seed_directory(
        project["id"], parent_id=docs["id"], name="api", description="HTTP endpoint reference."
    )
    repository.seed_file(
        project["id"], directory_id=api["id"], name="users.md", summary="User endpoints."
    )
    return project, root_id, docs, api


def _matching() -> ScriptedNavigator:
    """A navigator that walks ``root → docs → docs/api``."""
    return ScriptedNavigator(matches={"": [("docs", 0.9)], "docs": [("api", 0.9)]})


async def _suggest(service, project, *, filename: str = "auth.md", data: bytes = DOC):
    return await service.suggest(
        owner_id="user-1", project_id=project["id"], filename=filename, data=data
    )


async def _place(service, payload, **kwargs):
    return await service.place(
        owner_id="user-1",
        request_id=payload["request_id"],
        directory_id=kwargs.pop("directory_id", payload["suggestions"][0]["directory_id"]),
        placement=kwargs.pop("placement", PlacementMode.DIRECT),
        new_directory_name=kwargs.pop("new_directory_name", None),
        file_name=kwargs.pop("file_name", None),
    )


async def test_suggest_returns_the_matching_leaf_and_stages_the_blob() -> None:
    service, repository, store = _service(_matching())
    project, *_ = _seed(repository)

    payload = await _suggest(service, project)

    assert payload["suggestions"][0]["path"] == "docs/api"
    assert payload["suggestions"][0]["reason"] == "Because of api."
    assert payload["suggestions"][-1]["path"] == ""  # the root option is always offered
    assert payload["traversal"]["model"] == "scripted"
    assert payload["file"]["summary"] == "Summary of auth.md."
    assert store.objects
    stored = repository.requests[payload["request_id"]]
    assert stored["status"] == "suggested"
    assert stored["suggestions"] == payload["suggestions"]


async def test_suggest_flags_a_clashing_name_with_alternatives() -> None:
    service, repository, _ = _service(_matching())
    project, _, _, api = _seed(repository)
    repository.seed_file(
        project["id"], directory_id=api["id"], name="auth.md", summary="Existing auth notes."
    )

    payload = await _suggest(service, project)

    top = payload["suggestions"][0]
    assert top["name_available"] is False
    assert top["suggested_file_names"][0] == "auth-2.md"


async def test_suggest_points_at_identical_content_elsewhere() -> None:
    service, repository, _ = _service(_matching())
    project, root_id, _, _ = _seed(repository)
    repository.seed_file(
        project["id"],
        directory_id=root_id,
        name="auth.md",
        summary="The same document.",
        content_sha256=content_hash(DOC),
    )

    payload = await _suggest(service, project)

    assert payload["suggestions"][0]["identical_content_at"] == ["auth.md"]


async def test_suggest_rejects_a_non_markdown_upload() -> None:
    service, repository, _ = _service(_matching())
    project, *_ = _seed(repository)

    with pytest.raises(HTTPException) as excinfo:
        await _suggest(service, project, filename="diagram.png", data=b"\x89PNG")

    assert excinfo.value.status_code == 415
    assert "markdown" in str(excinfo.value.detail)


async def test_suggest_requires_an_owned_project() -> None:
    service, repository, _ = _service(_matching())
    project, *_ = _seed(repository)

    with pytest.raises(HTTPException) as excinfo:
        await service.suggest(
            owner_id="someone-else",
            project_id=project["id"],
            filename="auth.md",
            data=DOC,
        )

    assert excinfo.value.status_code == 404


async def test_a_failed_summary_is_a_retryable_502() -> None:
    service, repository, _ = _service(ScriptedNavigator(fail_summarising=True))
    project, *_ = _seed(repository)

    with pytest.raises(HTTPException) as excinfo:
        await _suggest(service, project)

    assert excinfo.value.status_code == 502


async def test_place_direct_writes_the_file_and_refreshes_ancestors() -> None:
    service, repository, store = _service(_matching())
    project, *_ = _seed(repository)
    payload = await _suggest(service, project)

    result = await _place(service, payload)

    assert result["created_directory"] is False
    assert result["file"]["path"] == "docs/api/auth.md"
    assert result["refreshed_directories"] == 3

    directories = {row["path"]: row for row in await repository.list_directories(project["id"])}
    assert directories["docs/api"]["direct_file_count"] == 2
    assert "auth.md" in directories["docs/api"]["description"]
    assert "api" in directories["docs"]["description"]
    assert "docs" in directories[""]["description"]

    project_row = await repository.get_project(project["id"])
    assert "docs" in project_row["description"]
    assert repository.requests[payload["request_id"]]["status"] == "placed"
    assert len(store.objects) == 1


async def test_place_in_a_new_directory_creates_it_under_the_chosen_one() -> None:
    service, repository, _ = _service(_matching())
    project, *_ = _seed(repository)
    payload = await _suggest(service, project)

    result = await _place(
        service,
        payload,
        placement=PlacementMode.NEW_DIRECTORY,
        new_directory_name="authentication",
    )

    assert result["created_directory"] is True
    assert result["directory_path"] == "docs/api/authentication"
    assert result["file"]["path"] == "docs/api/authentication/auth.md"

    directories = {row["path"]: row for row in await repository.list_directories(project["id"])}
    created = directories["docs/api/authentication"]
    assert created["depth"] == 3
    assert created["ltree_path"] == "docs.api.authentication"
    assert created["direct_file_count"] == 1
    assert "auth.md" in created["description"]
    assert directories["docs/api"]["child_directory_count"] == 1
    assert directories["docs/api"]["direct_file_count"] == 1


async def test_place_rejects_a_file_name_clash_with_alternatives() -> None:
    service, repository, _ = _service(_matching())
    project, _, _, api = _seed(repository)
    repository.seed_file(
        project["id"], directory_id=api["id"], name="auth.md", summary="Existing auth notes."
    )
    payload = await _suggest(service, project)

    with pytest.raises(HTTPException) as excinfo:
        await _place(service, payload)

    assert excinfo.value.status_code == 409
    detail = excinfo.value.detail
    assert detail["conflict"]["path"] == "docs/api/auth.md"
    assert detail["suggested_names"][0] == "auth-2.md"


async def test_place_can_rename_instead_of_failing() -> None:
    service, repository, _ = _service(_matching())
    project, _, _, api = _seed(repository)
    repository.seed_file(
        project["id"], directory_id=api["id"], name="auth.md", summary="Existing auth notes."
    )
    payload = await _suggest(service, project)

    result = await _place(service, payload, file_name="auth-2.md")

    assert result["file"]["path"] == "docs/api/auth-2.md"


async def test_place_rejects_a_clashing_new_directory() -> None:
    service, repository, _ = _service(_matching())
    project, _, _, api = _seed(repository)
    repository.seed_directory(project["id"], parent_id=api["id"], name="authentication")
    payload = await _suggest(service, project)

    with pytest.raises(HTTPException) as excinfo:
        await _place(
            service,
            payload,
            placement=PlacementMode.NEW_DIRECTORY,
            new_directory_name="authentication",
        )

    assert excinfo.value.status_code == 409
    assert excinfo.value.detail["suggested_names"][0] == "authentication-2"


async def test_place_allows_the_same_content_at_another_path() -> None:
    service, repository, _ = _service(_matching())
    project, _, docs, _ = _seed(repository)

    first = await _suggest(service, project)
    await _place(service, first)
    second = await _suggest(service, project)

    assert second["suggestions"][0]["identical_content_at"] == ["docs/api/auth.md"]
    result = await _place(service, second, directory_id=docs["id"])
    assert result["file"]["path"] == "docs/auth.md"

    files = await repository.list_files(project["id"])
    assert {row["path"] for row in files} == {
        "docs/api/users.md",
        "docs/api/auth.md",
        "docs/auth.md",
    }


async def test_place_rejects_an_expired_request() -> None:
    service, repository, _ = _service(_matching())
    project, *_ = _seed(repository)
    payload = await _suggest(service, project)
    repository.requests[payload["request_id"]]["expires_at"] = (
        datetime.now(UTC) - timedelta(minutes=1)
    ).isoformat()

    with pytest.raises(HTTPException) as excinfo:
        await _place(service, payload)

    assert excinfo.value.status_code == 410
    assert repository.requests[payload["request_id"]]["status"] == "expired"


async def test_place_is_single_use() -> None:
    service, repository, _ = _service(_matching())
    project, *_ = _seed(repository)
    payload = await _suggest(service, project)
    await _place(service, payload)

    with pytest.raises(HTTPException) as excinfo:
        await _place(service, payload)

    assert excinfo.value.status_code == 409


async def test_place_rejects_a_directory_from_another_project() -> None:
    service, repository, _ = _service(_matching())
    project, *_ = _seed(repository)
    other = repository.seed_project()
    payload = await _suggest(service, project)

    with pytest.raises(HTTPException) as excinfo:
        await _place(service, payload, directory_id=other["root_directory_id"])

    assert excinfo.value.status_code == 404


async def test_get_request_replays_the_suggestions() -> None:
    service, repository, _ = _service(_matching())
    project, *_ = _seed(repository)
    payload = await _suggest(service, project)

    replay = await service.get_request(payload["request_id"], "user-1")

    assert replay["suggestions"] == payload["suggestions"]
    assert replay["file"]["name"] == "auth.md"
    assert replay["status"] == "suggested"

    with pytest.raises(HTTPException) as excinfo:
        await service.get_request(payload["request_id"], "someone-else")
    assert excinfo.value.status_code == 404


async def test_a_rejected_folder_name_creates_nothing() -> None:
    service, repository, _ = _service(_matching())
    project, _, _, api = _seed(repository)
    repository.seed_directory(project["id"], parent_id=api["id"], name="authentication")
    payload = await _suggest(service, project)
    before = len(await repository.list_directories(project["id"]))

    with pytest.raises(HTTPException) as excinfo:
        await _place(
            service,
            payload,
            placement=PlacementMode.NEW_DIRECTORY,
            new_directory_name="authentication",
        )

    assert excinfo.value.status_code == 409
    assert len(await repository.list_directories(project["id"])) == before


async def test_an_unknown_placement_is_rejected() -> None:
    service, repository, _ = _service(_matching())
    project, *_ = _seed(repository)
    payload = await _suggest(service, project)

    with pytest.raises(HTTPException) as excinfo:
        await _place(service, payload, placement="sideways")

    assert excinfo.value.status_code == 400
