"""End-to-end behaviour of the pipeline against in-memory collaborators."""

from __future__ import annotations

import asyncio
from typing import Any

import pytest
from fastapi import HTTPException

from app.core.config import get_settings
from app.graph_creation.describe import Description, MockDescriber
from app.graph_creation.schemas import UploadMode
from app.graph_creation.service import GraphCreationService
from app.graph_creation.tests.fakes import (
    InMemoryGraphRepository,
    InMemoryObjectStore,
    RecordingDescriber,
)
from app.graph_creation.tree import FileEntry


def _service(describer: MockDescriber | None = None, settings: Any | None = None):
    repository = InMemoryGraphRepository()
    store = InMemoryObjectStore()
    service = GraphCreationService(
        repository=repository,
        store=store,
        describer=describer or MockDescriber(),
        settings=settings or get_settings(),
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
    """Describer whose model calls all fail (as a retired model would)."""

    async def describe_directory(self, *, path: str, files: Any, directories: Any) -> Description:
        raise RuntimeError("gemini exploded")


async def test_failed_descriptions_are_reported_on_the_job() -> None:
    service, repository, _ = _service(_BrokenDescriber())
    prepared = await service.prepare(
        owner_id="user-1", mode=UploadMode.NEW, entries=[FileEntry("a.md", b"# A")]
    )

    await service.run_job(prepared)

    job = await repository.get_job(prepared.job["id"])
    files = await repository.list_files(prepared.project["id"])
    directories = await repository.list_directories(prepared.project["id"])

    assert job["status"] == "partial"
    assert "item(s) failed" in job["error"]
    assert "gemini exploded" in job["error"]
    # A failed folder stores nothing, rather than text that would poison search.
    assert directories[0]["description"] is None
    assert directories[0]["description_model"] is None
    # The document is still stored; only the folder description failed.
    assert files[0]["summary_status"] == "skipped"
    assert files[0]["summary"] is None


class _PathFailingDescriber(MockDescriber):
    """Fails only for one folder, so its sibling and parent can still be checked."""

    def __init__(self, failing: str) -> None:
        super().__init__()
        self.failing = failing

    async def describe_directory(self, *, path: str, files: Any, directories: Any) -> Description:
        if path == self.failing:
            raise RuntimeError("model refused")
        return await super().describe_directory(path=path, files=files, directories=directories)


async def test_one_failed_folder_does_not_stop_its_sibling_or_parent() -> None:
    service, repository, _ = _service(_PathFailingDescriber("docs/api"))
    prepared = await service.prepare(
        owner_id="user-1",
        mode=UploadMode.NEW,
        entries=[
            FileEntry("docs/api/auth.md", b"# Auth"),
            FileEntry("docs/guide.md", b"# Guide"),
        ],
    )

    await service.run_job(prepared)

    project_id = prepared.project["id"]
    directories = {row["path"]: row for row in await repository.list_directories(project_id)}
    job = await repository.get_job(prepared.job["id"])

    assert directories["docs/api"]["description"] is None
    assert directories["docs/api"]["description_model"] is None
    assert directories["docs"]["description"]
    assert directories[""]["description"]
    assert job["status"] == "partial"
    assert "docs/api" in job["error"] and "model refused" in job["error"]


async def test_the_model_that_answered_is_recorded_per_folder() -> None:
    service, repository, _ = _service()
    prepared = await service.prepare(
        owner_id="user-1", mode=UploadMode.NEW, entries=[FileEntry("docs/a.md", b"# A")]
    )

    await service.run_job(prepared)

    directories = {
        row["path"]: row for row in await repository.list_directories(prepared.project["id"])
    }
    assert directories["docs"]["description_model"] == "mock"
    assert directories[""]["description_model"] == "mock"


class _ConcurrentDescriber(MockDescriber):
    """Records the peak number of descriptions in flight."""

    def __init__(self, delay: float = 0.02) -> None:
        self.delay = delay
        self.active = 0
        self.peak = 0

    async def describe_directory(self, *, path: str, files: Any, directories: Any) -> Description:
        self.active += 1
        self.peak = max(self.peak, self.active)
        try:
            await asyncio.sleep(self.delay)
            return await super().describe_directory(path=path, files=files, directories=directories)
        finally:
            self.active -= 1


async def test_sibling_folders_are_described_concurrently() -> None:
    describer = _ConcurrentDescriber()
    settings = get_settings().model_copy(update={"summary_concurrency": 3})
    service, repository, _ = _service(describer, settings)
    prepared = await service.prepare(
        owner_id="user-1",
        mode=UploadMode.NEW,
        entries=[
            FileEntry("a/one.md", b"# One"),
            FileEntry("b/two.md", b"# Two"),
            FileEntry("c/three.md", b"# Three"),
        ],
    )

    await service.run_job(prepared)

    assert describer.peak == 3
    job = await repository.get_job(prepared.job["id"])
    assert job["status"] == "ok"
    assert job["processed_files"] == 3


class _PromptRecordingDescriber(MockDescriber):
    """Keeps the subfolder descriptions each folder was given."""

    def __init__(self) -> None:
        super().__init__()
        self.subfolders: dict[str, list[tuple[str, str]]] = {}

    async def describe_directory(self, *, path: str, files: Any, directories: Any) -> Description:
        self.subfolders[path] = list(directories)
        return await super().describe_directory(path=path, files=files, directories=directories)


async def test_a_parent_is_described_from_its_childrens_descriptions() -> None:
    describer = _PromptRecordingDescriber()
    service, _, _ = _service(describer)
    prepared = await service.prepare(
        owner_id="user-1",
        mode=UploadMode.NEW,
        entries=[FileEntry("docs/api/auth.md", b"# Auth")],
    )

    await service.run_job(prepared)

    assert [name for name, _ in describer.subfolders["docs"]] == ["api"]
    child_description = describer.subfolders["docs"][0][1]
    assert child_description != "no description"
    assert [name for name, _ in describer.subfolders[""]] == ["docs"]
    assert describer.subfolders[""][0][1].startswith("docs holds")


class _VerboseDescriber(MockDescriber):
    """Returns far more text than a description should ever store."""

    async def describe_directory(self, *, path: str, files: Any, directories: Any) -> Description:
        return Description(text="word " * 200, model="verbose")


async def test_every_description_is_clipped_to_the_character_cap() -> None:
    service, repository, _ = _service(_VerboseDescriber())
    prepared = await service.prepare(
        owner_id="user-1",
        mode=UploadMode.NEW,
        entries=[FileEntry("docs/a.md", b"# A"), FileEntry("README.md", b"# Root")],
    )

    await service.run_job(prepared)

    for row in await repository.list_directories(prepared.project["id"]):
        assert row["description"]
        assert len(row["description"]) <= 300
        assert row["description"].endswith("…")


async def test_the_add_refresh_is_clipped_too() -> None:
    service, repository, _ = _service(_VerboseDescriber())
    first = await service.prepare(
        owner_id="user-1", mode=UploadMode.NEW, entries=[FileEntry("docs/a.md", b"# A")]
    )
    await service.run_job(first)
    project_id = first.project["id"]

    second = await service.prepare(
        owner_id="user-1",
        mode=UploadMode.ADD,
        project_id=project_id,
        entries=[FileEntry("docs/b.md", b"# B")],
    )
    await service.run_job(second)

    for row in await repository.list_directories(project_id):
        assert row["description"]
        assert len(row["description"]) <= 300


async def _one_document(
    entries: list[FileEntry] | None = None, settings: Any | None = None
) -> tuple[GraphCreationService, InMemoryGraphRepository, InMemoryObjectStore, list[dict]]:
    """Upload a tiny project and return the service plus its file rows."""
    service, repository, store = _service(settings=settings)
    prepared = await service.prepare(
        owner_id="user-1",
        mode=UploadMode.NEW,
        name="Docs",
        entries=entries or [FileEntry("docs/guide.md", b"# Guide\n\nOriginal.")],
    )
    await service.run_job(prepared)
    files = await repository.list_files(prepared.project["id"])
    return service, repository, store, files


async def test_a_document_body_can_be_read_back() -> None:
    service, _, _, files = await _one_document()

    content = await service.get_file_content(files[0]["id"], "user-1")

    assert content["text"] == "# Guide\n\nOriginal."
    assert content["path"] == "docs/guide.md"
    assert content["editable"] is True
    assert content["truncated"] is False
    assert content["content_sha256"] == files[0]["content_sha256"]


async def test_saving_stores_a_new_object_and_repoints_the_row() -> None:
    service, repository, store, files = await _one_document()
    original = files[0]
    old_path = original["storage_path"]

    saved = await service.save_file_content(
        original["id"],
        "user-1",
        text="# Guide\n\nEdited.",
        expected_sha256=original["content_sha256"],
    )

    assert saved["content_sha256"] != original["content_sha256"]
    assert saved["storage_path"] != old_path
    assert saved["size_bytes"] == len(b"# Guide\n\nEdited.")
    assert store.objects[saved["storage_path"]] == b"# Guide\n\nEdited."
    # Blobs are content-addressed and shared, so the old object is never overwritten.
    assert store.objects[old_path] == b"# Guide\n\nOriginal."
    row = await repository.get_file(original["id"])
    assert row["storage_path"] == saved["storage_path"]
    assert row["content_sha256"] == saved["content_sha256"]


async def test_editing_one_of_two_identical_documents_leaves_the_other_alone() -> None:
    service, repository, store, files = await _one_document(
        [FileEntry("docs/a.md", b"# Same"), FileEntry("docs/b.md", b"# Same")]
    )
    first, second = files
    shared = first["storage_path"]
    assert second["storage_path"] == shared

    await service.save_file_content(first["id"], "user-1", text="# Changed")

    untouched = await repository.get_file(second["id"])
    assert untouched["storage_path"] == shared
    assert store.objects[shared] == b"# Same"


async def test_a_stale_digest_is_refused() -> None:
    service, _, _, files = await _one_document()

    with pytest.raises(HTTPException) as excinfo:
        await service.save_file_content(
            files[0]["id"], "user-1", text="# New", expected_sha256="not-the-current-digest"
        )

    assert excinfo.value.status_code == 409


async def test_an_oversized_body_is_refused() -> None:
    from app.core.config import Settings

    service, _, _, files = await _one_document(
        [FileEntry("docs/a.md", b"# A")], settings=Settings(max_file_bytes=16)
    )

    with pytest.raises(HTTPException) as excinfo:
        await service.save_file_content(files[0]["id"], "user-1", text="x" * 17)

    assert excinfo.value.status_code == 413


async def test_another_users_document_is_not_found() -> None:
    service, _, _, files = await _one_document()

    with pytest.raises(HTTPException) as excinfo:
        await service.get_file_content(files[0]["id"], "someone-else")

    assert excinfo.value.status_code == 404


async def test_a_document_over_the_read_cap_opens_read_only() -> None:
    from app.core.config import Settings

    service, _, _, files = await _one_document(
        [FileEntry("docs/big.md", b"# Big\n\n" + b"x" * 1_200)],
        settings=Settings(file_edit_max_chars=1_000),
    )

    content = await service.get_file_content(files[0]["id"], "user-1")

    assert content["truncated"] is True
    assert content["editable"] is False
    assert len(content["text"]) == 1_000
