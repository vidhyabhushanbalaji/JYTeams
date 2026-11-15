"""Sharing: membership decides access, and the project list says which role you have."""

from __future__ import annotations

import pytest
from fastapi import HTTPException

from app.core.activity import DOCUMENT_SAVED
from app.core.config import get_settings
from app.graph_creation.service import GraphCreationService
from app.graph_creation.tests.fakes import (
    FakeProjectAccess,
    InMemoryGraphRepository,
    InMemoryObjectStore,
    RecordingActivityLog,
    RecordingDescriber,
)


def _service(
    repository: InMemoryGraphRepository, access: FakeProjectAccess, activity: RecordingActivityLog
) -> GraphCreationService:
    return GraphCreationService(
        repository=repository,
        store=InMemoryObjectStore(),
        describer=RecordingDescriber(),
        settings=get_settings(),
        access=access,
        activity=activity,
    )


@pytest.fixture()
def shared():
    repository = InMemoryGraphRepository()
    access = FakeProjectAccess()
    activity = RecordingActivityLog()
    project = repository.projects.setdefault(
        "project-1", {"id": "project-1", "owner_id": "ada", "name": "Pulse"}
    )
    access.grant(project["id"], "ada")
    access.grant(project["id"], "bo")
    return repository, access, activity, project


async def test_a_member_can_read_a_shared_project(shared) -> None:
    repository, access, activity, project = shared
    service = _service(repository, access, activity)

    row = await service.get_project(project["id"], "bo")

    assert row["id"] == project["id"]
    assert row["role"] == "member"


async def test_the_creator_is_the_owner(shared) -> None:
    repository, access, activity, project = shared
    service = _service(repository, access, activity)

    assert (await service.get_project(project["id"], "ada"))["role"] == "owner"


async def test_a_stranger_is_still_404(shared) -> None:
    repository, access, activity, project = shared
    service = _service(repository, access, activity)

    with pytest.raises(HTTPException) as error:
        await service.get_project(project["id"], "cy")

    assert error.value.status_code == 404


async def test_the_project_list_includes_shared_projects(shared) -> None:
    repository, access, activity, project = shared
    service = _service(repository, access, activity)

    listed = await service.list_projects("bo")

    assert [row["id"] for row in listed] == [project["id"]]
    assert listed[0]["role"] == "member"


async def test_saving_a_document_records_an_activity_event(shared) -> None:
    repository, access, activity, project = shared
    service = _service(repository, access, activity)
    inserted = await repository.insert_files(
        [
            {
                "project_id": project["id"],
                "directory_id": "directory-1",
                "name": "auth.md",
                "path": "pulse/auth.md",
                "size_bytes": 4,
                "content_sha256": "old",
                "storage_bucket": "test-bucket",
                "storage_path": "old.md",
                "summary": None,
                "summary_status": "skipped",
            }
        ]
    )

    await service.save_file_content(inserted[0]["id"], "ada", text="# New body\n")

    assert [event["kind"] for event in activity.events] == [DOCUMENT_SAVED]
    assert activity.events[0]["detail"]["file_name"] == "auth.md"
