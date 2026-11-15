"""Graph Add's two steps: local suggestions, then one call to refresh the descriptions."""

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
    ScriptedDescriber,
)

ROOT_DESCRIPTION = "The project root: release documentation."
GUIDES_DESCRIPTION = "Deployment and release procedures, including rollback steps."
LEGAL_DESCRIPTION = "Licences and trademarks."
DOCUMENT = b"# Rollback runbook\n\nRoll back a failed release with the previous Helm chart.\n"


def _service(describer: ScriptedDescriber | None = None):
    repository = InMemoryAddRepository()
    store = InMemoryObjectStore()
    service = GraphAddService(
        repository=repository,
        store=store,
        describer=describer or ScriptedDescriber(),
        settings=get_settings(),
    )
    return service, repository, store


def _seed(repository: InMemoryAddRepository):
    project = repository.seed_project()
    root_id = project["root_directory_id"]
    repository.directories[root_id]["description"] = ROOT_DESCRIPTION
    repository.seed_file(project["id"], directory_id=root_id, name="README.md")
    guides = repository.seed_directory(
        project["id"], parent_id=root_id, name="guides", description=GUIDES_DESCRIPTION
    )
    repository.seed_file(project["id"], directory_id=guides["id"], name="deployment.md")
    repository.seed_directory(
        project["id"], parent_id=root_id, name="legal", description=LEGAL_DESCRIPTION
    )
    return project, guides


async def _suggest(service, project, **kwargs: object):
    return await service.suggest(
        owner_id=kwargs.pop("owner", "user-1"),  # type: ignore[arg-type]
        project_id=project["id"],
        filename=kwargs.pop("filename", "rollback-runbook.md"),  # type: ignore[arg-type]
        data=kwargs.pop("data", DOCUMENT),  # type: ignore[arg-type]
    )


async def test_suggest_ranks_locally_without_calling_a_model() -> None:
    describer = ScriptedDescriber()
    service, repository, _ = _service(describer)
    project, _ = _seed(repository)

    payload = await _suggest(service, project)

    assert payload["suggestions"][0]["path"] == "guides"
    assert payload["suggestions"][0]["score"] > 0
    assert "rollback" in payload["suggestions"][0]["matched_terms"]
    assert payload["suggestions"][-1]["path"] == ""
    assert payload["file"]["preview"].startswith("# Rollback runbook")
    assert payload["scan"]["folders_scored"] == 3
    assert payload["scan"]["scorer_version"]
    assert describer.calls == []


async def test_the_request_row_holds_everything_placement_needs() -> None:
    service, repository, _ = _service()
    project, _ = _seed(repository)

    payload = await _suggest(service, project)

    request = await repository.get_add_request(payload["request_id"])
    assert request is not None
    assert request["status"] == "suggested"
    assert request["summary"] == payload["file"]["preview"]
    assert request["storage_path"]
    assert request["suggestions"] == payload["suggestions"]
    assert request["traversal"] == payload["scan"]


async def test_identical_content_already_in_the_tree_is_reported() -> None:
    service, repository, _ = _service()
    project, guides = _seed(repository)
    repository.seed_file(
        project["id"],
        directory_id=guides["id"],
        name="old-runbook.md",
        content_sha256=content_hash(DOCUMENT),
    )

    payload = await _suggest(service, project)

    top = payload["suggestions"][0]
    assert top["path"] == "guides"
    assert top["identical_content_at"] == ["guides/old-runbook.md"]


async def test_a_name_clash_comes_back_with_alternatives() -> None:
    service, repository, _ = _service()
    project, guides = _seed(repository)
    repository.seed_file(project["id"], directory_id=guides["id"], name="rollback-runbook.md")

    payload = await _suggest(service, project)

    top = payload["suggestions"][0]
    assert top["path"] == "guides"
    assert top["name_available"] is False
    assert top["suggested_file_names"]


async def test_a_non_markdown_document_is_rejected() -> None:
    service, repository, _ = _service()
    project, _ = _seed(repository)

    with pytest.raises(HTTPException) as excinfo:
        await _suggest(service, project, filename="diagram.png", data=b"\x89PNG\r\n")

    assert excinfo.value.status_code == 415


async def test_a_project_without_a_tree_is_a_conflict() -> None:
    service, repository, _ = _service()
    project = repository.seed_project()
    repository.directories.clear()

    with pytest.raises(HTTPException) as excinfo:
        await _suggest(service, project)

    assert excinfo.value.status_code == 409


async def test_another_users_project_is_not_found() -> None:
    service, repository, _ = _service()
    project, _ = _seed(repository)

    with pytest.raises(HTTPException) as excinfo:
        await _suggest(service, project, owner="someone-else")

    assert excinfo.value.status_code == 404


async def _place(
    service,
    suggestion,
    *,
    directory_id: str,
    placement: PlacementMode = PlacementMode.DIRECT,
    new_directory_name: str | None = None,
    file_name: str | None = None,
    owner: str = "user-1",
):
    return await service.place(
        owner_id=owner,
        request_id=suggestion["request_id"],
        directory_id=directory_id,
        placement=placement,
        new_directory_name=new_directory_name,
        file_name=file_name,
    )


async def test_a_direct_placement_refreshes_the_chain_in_one_call() -> None:
    describer = ScriptedDescriber()
    service, repository, _ = _service(describer)
    project, guides = _seed(repository)
    suggestion = await _suggest(service, project)

    result = await _place(service, suggestion, directory_id=guides["id"])

    assert result["created_directory"] is False
    assert result["directory_path"] == "guides"
    assert result["refreshed_directories"] == 2
    assert describer.calls == [("guides", "")]
    assert result["file"]["summary_status"] == "skipped"

    directories = {row["path"]: row for row in await repository.list_directories(project["id"])}
    assert directories["guides"]["direct_file_count"] == 2
    assert "rollback runbook" in directories["guides"]["description"]
    assert "rollback runbook" in directories[""]["description"]
    project_row = await repository.get_project(project["id"])
    assert project_row["description"] == directories[""]["description"]

    request = await repository.get_add_request(suggestion["request_id"])
    assert request["status"] == "placed"
    assert request["placed_file_id"] == result["file"]["id"]


async def test_the_placed_document_text_reaches_the_describer() -> None:
    describer = ScriptedDescriber()
    service, repository, _ = _service(describer)
    project, guides = _seed(repository)
    suggestion = await _suggest(service, project)

    await _place(service, suggestion, directory_id=guides["id"])

    document = describer.documents[0]
    assert document.name == "rollback-runbook.md"
    assert document.directory_path == "guides"
    assert "Rollback runbook" in document.text


async def test_a_new_folder_is_described_by_the_same_call() -> None:
    describer = ScriptedDescriber()
    service, repository, _ = _service(describer)
    project, guides = _seed(repository)
    suggestion = await _suggest(service, project)

    result = await _place(
        service,
        suggestion,
        directory_id=guides["id"],
        placement=PlacementMode.NEW_DIRECTORY,
        new_directory_name="runbooks",
    )

    assert result["created_directory"] is True
    assert result["directory_path"] == "guides/runbooks"
    # One call, covering the new folder, its parent and the root, deepest first.
    assert describer.calls == [("guides/runbooks", "guides", "")]
    assert result["refreshed_directories"] == 3

    directories = {row["path"]: row for row in await repository.list_directories(project["id"])}
    assert directories["guides/runbooks"]["direct_file_count"] == 1
    assert directories["guides/runbooks"]["description"]
    assert directories["guides"]["child_directory_count"] == 1


async def test_a_rename_is_honoured() -> None:
    service, repository, _ = _service()
    project, guides = _seed(repository)
    suggestion = await _suggest(service, project)

    result = await _place(service, suggestion, directory_id=guides["id"], file_name="rollback.md")

    assert result["file"]["path"] == "guides/rollback.md"


async def test_a_describer_failure_keeps_the_placement_and_the_old_descriptions() -> None:
    describer = ScriptedDescriber(fail=True)
    service, repository, _ = _service(describer)
    project, guides = _seed(repository)
    suggestion = await _suggest(service, project)

    result = await _place(service, suggestion, directory_id=guides["id"])

    assert result["refreshed_directories"] == 2
    directories = {row["path"]: row for row in await repository.list_directories(project["id"])}
    assert directories["guides"]["description"] == GUIDES_DESCRIPTION
    assert directories[""]["description"] == ROOT_DESCRIPTION
    assert directories["guides"]["direct_file_count"] == 2


async def test_an_unreadable_document_still_updates_the_descriptions() -> None:
    describer = ScriptedDescriber()
    service, repository, store = _service(describer)
    project, guides = _seed(repository)
    suggestion = await _suggest(service, project)
    store.objects.clear()

    result = await _place(service, suggestion, directory_id=guides["id"])

    assert result["refreshed_directories"] == 2
    assert describer.calls == [("guides", "")]
    assert describer.documents[0].text == ""


async def test_a_second_placement_is_refused() -> None:
    service, repository, _ = _service()
    project, guides = _seed(repository)
    suggestion = await _suggest(service, project)
    await _place(service, suggestion, directory_id=guides["id"])

    with pytest.raises(HTTPException) as excinfo:
        await _place(service, suggestion, directory_id=guides["id"])

    assert excinfo.value.status_code == 409


async def test_an_expired_suggestion_is_gone() -> None:
    service, repository, _ = _service()
    project, guides = _seed(repository)
    suggestion = await _suggest(service, project)
    repository.requests[suggestion["request_id"]]["expires_at"] = (
        datetime.now(UTC) - timedelta(hours=1)
    ).isoformat()

    with pytest.raises(HTTPException) as excinfo:
        await _place(service, suggestion, directory_id=guides["id"])

    assert excinfo.value.status_code == 410


async def test_an_unknown_directory_is_not_found() -> None:
    service, repository, _ = _service()
    project, _ = _seed(repository)
    suggestion = await _suggest(service, project)

    with pytest.raises(HTTPException) as excinfo:
        await _place(service, suggestion, directory_id="directory-999")

    assert excinfo.value.status_code == 404


async def test_another_users_suggestion_is_not_found() -> None:
    service, repository, _ = _service()
    project, guides = _seed(repository)
    suggestion = await _suggest(service, project)

    with pytest.raises(HTTPException) as excinfo:
        await _place(service, suggestion, directory_id=guides["id"], owner="someone-else")

    assert excinfo.value.status_code == 404


async def test_replaying_a_suggestion_returns_the_preview_and_the_scan() -> None:
    service, repository, _ = _service()
    project, _ = _seed(repository)
    suggestion = await _suggest(service, project)

    replay = await service.get_request(suggestion["request_id"], "user-1")

    assert replay["file"]["preview"].startswith("# Rollback runbook")
    assert replay["scan"]["folders_scored"] == 3
    assert replay["suggestions"] == suggestion["suggestions"]
