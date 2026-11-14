"""End-to-end behaviour of the pipeline against in-memory collaborators."""

from __future__ import annotations

from typing import Any

import pytest
from fastapi import HTTPException

from app.core.config import get_settings
from app.graph_creation.describe import MockDescriber
from app.graph_creation.schemas import UploadMode
from app.graph_creation.service import GraphCreationService
from app.graph_creation.tests.fakes import (
    InMemoryGraphRepository,
    InMemoryObjectStore,
    RecordingDescriber,
)
from app.graph_creation.tree import FileEntry


def _service(describer: MockDescriber | None = None):
    repository = InMemoryGraphRepository()
    store = InMemoryObjectStore()
    service = GraphCreationService(
        repository=repository,
        store=store,
        describer=describer or MockDescriber(),
        settings=get_settings(),
    )
    return service, repository, store


async def test_new_upload_builds_a_described_tree() -> None:
    service, repository, store = _service()
    prepared = await service.prepare(
        owner_id="user-1",
        mode=UploadMode.NEW,
        name="Docs",
        entries=[
            FileEntry("README.md", b"# Project\n\nTop level notes."),
            FileEntry("docs/guide.md", b"# Guide\n\nGetting started."),
            FileEntry("docs/api/auth.md", b"# Auth\n\nHow auth works."),
            FileEntry("docs/api/users.md", b"# Users\n\nUser endpoints."),
        ],
    )

    await service.run_job(prepared)

    project_id = prepared.project["id"]
    directories = {row["path"]: row for row in await repository.list_directories(project_id)}
    files = {row["path"]: row for row in await repository.list_files(project_id)}

    assert set(directories) == {"", "docs", "docs/api"}
    assert set(files) == {"README.md", "docs/guide.md", "docs/api/auth.md", "docs/api/users.md"}

    assert directories["docs/api"]["child_directory_count"] == 0
    assert directories["docs/api"]["direct_file_count"] == 2
    assert directories["docs"]["direct_file_count"] == 1
    assert directories["docs"]["child_directory_count"] == 1
    assert directories[""]["description"]
    assert directories["docs/api"]["description"]

    assert files["docs/api/auth.md"]["summary_status"] == "skipped"
    assert files["docs/api/auth.md"]["summary"] is None
    assert files["docs/api/auth.md"]["storage_path"].endswith(".md")
    assert store.objects

    project = await repository.get_project(project_id)
    assert project["root_directory_id"] == directories[""]["id"]
    assert project["description"] == directories[""]["description"]

    job = await repository.get_job(prepared.job["id"])
    assert job["status"] == "ok"
    assert job["processed_files"] == 4
    assert job["failed_files"] == 0


async def test_descriptions_are_produced_bottom_up() -> None:
    describer = RecordingDescriber()
    service, _, _ = _service(describer)
    prepared = await service.prepare(
        owner_id="user-1",
        mode=UploadMode.NEW,
        entries=[FileEntry("docs/api/auth.md", b"# Auth\n\nHow auth works.")],
    )

    await service.run_job(prepared)

    directory_calls = [path for kind, path in describer.calls if kind == "directory"]
    assert directory_calls == ["docs/api", "docs", ""]


async def test_one_model_call_per_directory_and_the_file_text_reaches_it() -> None:
    """The point of the change: three files, two folders, two calls."""
    describer = RecordingDescriber()
    service, repository, _ = _service(describer)
    prepared = await service.prepare(
        owner_id="user-1",
        mode=UploadMode.NEW,
        entries=[
            FileEntry("docs/alpha.md", b"# Alpha\n\nDetails about alpha."),
            FileEntry("docs/beta.md", b"# Beta\n\nDetails about beta."),
            FileEntry("README.md", b"# Overview"),
        ],
    )

    await service.run_job(prepared)

    assert [path for kind, path in describer.calls if kind == "directory"] == ["docs", ""]
    directories = {
        row["path"]: row for row in await repository.list_directories(prepared.project["id"])
    }
    # The folder was described from the documents themselves, not from per-file summaries.
    assert "Alpha" in directories["docs"]["description"]
    assert "Beta" in directories["docs"]["description"]


async def test_unusable_files_are_stored_and_the_folder_is_still_described() -> None:
    describer = RecordingDescriber()
    service, repository, _ = _service(describer)
    prepared = await service.prepare(
        owner_id="user-1",
        mode=UploadMode.NEW,
        entries=[FileEntry("diagram.png", b"\x89PNG\r\n"), FileEntry("notes.md", b"# Notes")],
    )

    await service.run_job(prepared)

    files = {row["path"]: row for row in await repository.list_files(prepared.project["id"])}
    assert files["diagram.png"]["summary_status"] == "skipped"
    assert files["diagram.png"]["summary"] is None
    # One call for the folder, none for the individual documents.
    assert [kind for kind, _ in describer.calls] == ["directory"]


async def test_add_merges_into_the_existing_tree_and_refreshes_ancestors() -> None:
    service, repository, _ = _service()
    first = await service.prepare(
        owner_id="user-1",
        mode=UploadMode.NEW,
        entries=[FileEntry("docs/a.md", b"# A")],
    )
    await service.run_job(first)
    project_id = first.project["id"]

    second = await service.prepare(
        owner_id="user-1",
        mode=UploadMode.ADD,
        project_id=project_id,
        entries=[FileEntry("docs/b.md", b"# B"), FileEntry("notes/c.md", b"# C")],
    )
    await service.run_job(second)

    directories = {row["path"]: row for row in await repository.list_directories(project_id)}
    files = {row["path"]: row for row in await repository.list_files(project_id)}

    assert set(directories) == {"", "docs", "notes"}
    assert directories["docs"]["direct_file_count"] == 2
    assert set(files) == {"docs/a.md", "docs/b.md", "notes/c.md"}
    assert "notes" in directories[""]["description"]


async def test_add_rejects_paths_that_already_exist() -> None:
    service, _, _ = _service()
    first = await service.prepare(
        owner_id="user-1", mode=UploadMode.NEW, entries=[FileEntry("docs/a.md", b"# A")]
    )
    await service.run_job(first)

    with pytest.raises(HTTPException) as excinfo:
        await service.prepare(
            owner_id="user-1",
            mode=UploadMode.ADD,
            project_id=first.project["id"],
            entries=[FileEntry("docs/a.md", b"# A again")],
        )

    assert excinfo.value.status_code == 409


async def test_add_requires_an_owned_project() -> None:
    service, _, _ = _service()
    first = await service.prepare(
        owner_id="user-1", mode=UploadMode.NEW, entries=[FileEntry("a.md", b"# A")]
    )

    with pytest.raises(HTTPException) as missing_project:
        await service.prepare(
            owner_id="user-1", mode=UploadMode.ADD, entries=[FileEntry("b.md", b"# B")]
        )
    assert missing_project.value.status_code == 400

    with pytest.raises(HTTPException) as not_owned:
        await service.prepare(
            owner_id="someone-else",
            mode=UploadMode.ADD,
            project_id=first.project["id"],
            entries=[FileEntry("b.md", b"# B")],
        )
    assert not_owned.value.status_code == 404


async def test_tree_reads_are_nested_and_depth_limited() -> None:
    service, _, _ = _service()
    prepared = await service.prepare(
        owner_id="user-1",
        mode=UploadMode.NEW,
        entries=[
            FileEntry("docs/api/auth.md", b"# Auth"),
            FileEntry("README.md", b"# Root"),
        ],
    )
    await service.run_job(prepared)
    project_id = prepared.project["id"]

    full = await service.get_tree(project_id, "user-1")
    shallow = await service.get_tree(project_id, "user-1", max_depth=1)

    assert [child["path"] for child in full["tree"]["directories"]] == ["docs"]
    assert full["tree"]["directories"][0]["directories"][0]["path"] == "docs/api"
    assert shallow["tree"]["directories"] == []
    assert [item["path"] for item in shallow["tree"]["files"]] == ["README.md"]

    directory = await service.get_directory(full["tree"]["directories"][0]["id"], "user-1")
    assert [child["path"] for child in directory["directories"]] == ["docs/api"]
    assert directory["files"] == []


class _BrokenDescriber(MockDescriber):
    """Describer whose Gemini calls all fail (as a retired model would)."""

    async def describe_directory(self, *, path: str, files: Any, directories: Any) -> str:
        raise RuntimeError("gemini exploded")


async def test_failed_descriptions_are_reported_on_the_job() -> None:
    service, repository, _ = _service(_BrokenDescriber())
    prepared = await service.prepare(
        owner_id="user-1", mode=UploadMode.NEW, entries=[FileEntry("a.md", b"# A")]
    )

    await service.run_job(prepared)

    job = await repository.get_job(prepared.job["id"])
    files = await repository.list_files(prepared.project["id"])

    assert job["status"] == "partial"
    assert "item(s) failed" in job["error"]
    assert "gemini exploded" in job["error"]
    # The document is still stored; only the folder description failed.
    assert files[0]["summary_status"] == "skipped"
    assert files[0]["summary"] is None
