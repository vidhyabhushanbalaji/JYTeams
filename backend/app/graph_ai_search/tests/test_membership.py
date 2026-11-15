"""Search follows project membership, not the creator's id."""

from __future__ import annotations

import pytest
from fastapi import HTTPException

from app.core.access import ProjectAccess, ProjectRole
from app.core.config import get_settings
from app.graph_ai_search.scoring import LocalScorer
from app.graph_ai_search.service import GraphSearchService
from app.graph_ai_search.storage import BlobCache, DocumentTextReader
from app.graph_ai_search.tests.fakes import FakeBlobStore, InMemorySearchRepository


class _Membership(ProjectAccess):
    def __init__(self, roles: dict[tuple[str, str], ProjectRole]) -> None:
        self._roles = roles

    async def role(self, project_id: str, member_id: str) -> ProjectRole | None:
        return self._roles.get((project_id, member_id))

    async def project_ids(self, member_id: str) -> list[str]:
        return [project for (project, member) in self._roles if member == member_id]


def _service(repository: InMemorySearchRepository, access: ProjectAccess) -> GraphSearchService:
    return GraphSearchService(
        repository=repository,
        reader=DocumentTextReader(
            store=FakeBlobStore.from_repository(repository), cache=BlobCache(max_entries=4)
        ),
        scorer=LocalScorer(),
        settings=get_settings(),
        access=access,
    )


@pytest.fixture()
def shared():
    repository = InMemorySearchRepository()
    project = repository.seed_project(owner_id="ada")
    repository.seed_file(
        project["id"],
        directory_id=project["root_directory_id"],
        name="deployment.md",
        body="# Deployment\n\nA rollback restores the previous release.",
    )
    return repository, project


async def test_a_member_can_search_a_shared_project(shared) -> None:
    repository, project = shared
    access = _Membership({(project["id"], "bo"): ProjectRole.MEMBER})

    result = await _service(repository, access).search(
        project_id=project["id"], owner_id="bo", query="rollback"
    )

    assert result["results"][0]["name"] == "deployment.md"


async def test_a_stranger_cannot_search_a_project(shared) -> None:
    repository, project = shared
    access = _Membership({(project["id"], "ada"): ProjectRole.OWNER})

    with pytest.raises(HTTPException) as error:
        await _service(repository, access).search(
            project_id=project["id"], owner_id="bo", query="rollback"
        )

    assert error.value.status_code == 404
