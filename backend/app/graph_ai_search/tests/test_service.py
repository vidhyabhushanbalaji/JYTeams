"""Contract, payload and validation of the search service (local scorer, in-memory storage)."""

from __future__ import annotations

import pytest
from fastapi import HTTPException

from app.core.config import get_settings
from app.graph_ai_search.scoring import LocalScorer
from app.graph_ai_search.service import MAX_LIMIT, GraphSearchService
from app.graph_ai_search.storage import BlobCache, DocumentTextReader
from app.graph_ai_search.tests.fakes import FakeBlobStore, InMemorySearchRepository


def _seed(repository: InMemorySearchRepository):
    """A tiny PulseAPI lookalike: a root file, a reference folder and a guides folder."""
    project = repository.seed_project()
    root = project["root_directory_id"]
    repository.seed_file(
        project["id"],
        directory_id=root,
        name="README.md",
        body="# PulseAPI\n\nThe event ingestion service for distributed microservices.",
    )
    docs = repository.seed_directory(
        project["id"],
        parent_id=root,
        name="docs",
        description="API reference and architecture for event ingestion.",
    )
    repository.seed_file(
        project["id"],
        directory_id=docs["id"],
        name="api-reference.md",
        body="# API Reference\n\nBase URL, authentication and the event ingestion endpoints.",
    )
    repository.seed_file(
        project["id"],
        directory_id=docs["id"],
        name="architecture.md",
        body="# Architecture\n\nIngestion workers batch events and write them to TimescaleDB.",
    )
    guides = repository.seed_directory(
        project["id"],
        parent_id=root,
        name="guides",
        description="Deployment and release procedures for platform engineers.",
    )
    repository.seed_file(
        project["id"],
        directory_id=guides["id"],
        name="deployment.md",
        body="# Deployment\n\nRoll back a release with the previous Helm chart, then smoke test.",
    )
    return project


def _service(repository: InMemorySearchRepository, store: FakeBlobStore | None = None):
    store = store or FakeBlobStore.from_repository(repository)
    service = GraphSearchService(
        repository=repository,
        reader=DocumentTextReader(store=store, cache=BlobCache(max_entries=8)),
        scorer=LocalScorer(),
        settings=get_settings(),
    )
    return service, store


async def _search(service: GraphSearchService, project, **kwargs: object):
    return await service.search(
        project_id=project["id"],
        owner_id="user-1",
        query=kwargs.pop("query", "deployment release"),  # type: ignore[arg-type]
        **kwargs,  # type: ignore[arg-type]
    )


async def test_search_returns_ranked_hits_with_evidence() -> None:
    repository = InMemorySearchRepository()
    project = _seed(repository)
    service, _ = _service(repository)

    payload = await _search(service, project)

    assert set(payload) == {
        "query",
        "context",
        "project_id",
        "results",
        "directories",
        "opened_directories",
        "traversal",
    }
    assert payload["results"][0]["name"] == "deployment.md"
    assert payload["results"][0]["path"] == "guides/deployment.md"
    assert payload["results"][0]["directory_path"] == "guides"
    assert payload["results"][0]["score"] > 0
    assert "deployment" in payload["results"][0]["matched_terms"]
    assert payload["results"][0]["excerpt"]
    assert set(payload["traversal"]) == {
        "directories_visited",
        "directories_opened",
        "documents_considered",
        "files_read",
        "fallback_used",
        "degraded",
        "budget_exhausted",
        "scorer_version",
        "duration_ms",
    }
    assert payload["traversal"]["files_read"] > 0
    assert payload["traversal"]["scorer_version"] == LocalScorer().version


async def test_the_guides_branch_is_opened_from_its_description() -> None:
    repository = InMemorySearchRepository()
    project = _seed(repository)
    service, store = _service(repository)

    payload = await _search(service, project)

    assert "guides" in payload["opened_directories"]
    # The pruned branch is never read, which is the whole point of the description index.
    assert "docs" not in payload["opened_directories"]
    assert not any("api-reference" in path for path in store.reads)
    assert [hit["name"] for hit in payload["directories"]] == ["guides"]


async def test_context_widens_a_query_that_misses() -> None:
    repository = InMemorySearchRepository()
    project = _seed(repository)
    service, _ = _service(repository)

    without = await _search(service, project, query="zzz qqq")
    with_context = await _search(service, project, query="zzz qqq", context="deployment release")

    assert without["results"] == []
    assert [hit["name"] for hit in with_context["results"]] == ["deployment.md"]
    assert with_context["context"] == "deployment release"


async def test_limit_and_min_score_trim_the_results() -> None:
    repository = InMemorySearchRepository()
    project = _seed(repository)
    service, _ = _service(repository)

    limited = await _search(service, project, query="event", limit=1)
    filtered = await _search(service, project, query="event", min_score=0.99)

    assert len(limited["results"]) == 1
    assert all(hit["score"] >= 0.99 for hit in filtered["results"])


async def test_a_short_query_is_rejected() -> None:
    repository = InMemorySearchRepository()
    project = _seed(repository)
    service, _ = _service(repository)

    with pytest.raises(HTTPException) as excinfo:
        await _search(service, project, query="  ab  ")

    assert excinfo.value.status_code == 400
    assert "at least" in str(excinfo.value.detail)


async def test_over_long_inputs_are_rejected() -> None:
    repository = InMemorySearchRepository()
    project = _seed(repository)
    service, _ = _service(repository)

    with pytest.raises(HTTPException):
        await _search(service, project, query="x" * 501)
    with pytest.raises(HTTPException):
        await _search(service, project, query="deploy", context="x" * 501)


@pytest.mark.parametrize("limit", [0, MAX_LIMIT + 1])
async def test_limit_bounds_are_enforced(limit: int) -> None:
    repository = InMemorySearchRepository()
    project = _seed(repository)
    service, _ = _service(repository)

    with pytest.raises(HTTPException) as excinfo:
        await _search(service, project, limit=limit)

    assert excinfo.value.status_code == 400


async def test_other_numeric_bounds_are_enforced() -> None:
    repository = InMemorySearchRepository()
    project = _seed(repository)
    service, _ = _service(repository)

    with pytest.raises(HTTPException):
        await _search(service, project, min_score=1.5)
    with pytest.raises(HTTPException):
        await _search(service, project, max_directories=0)


async def test_another_users_project_is_not_found() -> None:
    repository = InMemorySearchRepository()
    project = _seed(repository)
    service, _ = _service(repository)

    with pytest.raises(HTTPException) as excinfo:
        await service.search(project_id=project["id"], owner_id="someone-else", query="deployment")

    assert excinfo.value.status_code == 404


async def test_a_project_without_a_tree_is_a_conflict() -> None:
    repository = InMemorySearchRepository()
    service, _ = _service(repository)
    empty = repository.seed_project()
    repository.directories.clear()

    with pytest.raises(HTTPException) as excinfo:
        await service.search(project_id=empty["id"], owner_id="user-1", query="deployment")

    assert excinfo.value.status_code == 409


async def test_an_unreadable_document_degrades_the_response() -> None:
    repository = InMemorySearchRepository()
    project = _seed(repository)
    store = FakeBlobStore.from_repository(repository)
    store.fail_paths.add(f"{project['id']}/deployment.md")
    service, _ = _service(repository, store)

    payload = await _search(service, project)

    assert payload["results"] == []
    assert payload["traversal"]["degraded"] is True


@pytest.mark.parametrize(
    ("file_name", "description"),
    [
        ("rollback-plan.md", "Rollback plans and recovery steps for a failed release."),
        ("rollback_plan.md", "Rollback plans and recovery steps for a failed release."),
        ("rollbackPlan.md", "Rollback plans and recovery steps for a failed release."),
        # Legacy descriptions written before the prose rule still match.
        ("rollback-plan.md", "Rollback-plan and recovery steps for a failed release."),
    ],
)
async def test_a_spaced_query_finds_a_compound_document_name(
    file_name: str, description: str
) -> None:
    repository = InMemorySearchRepository()
    project = repository.seed_project()
    operations = repository.seed_directory(
        project["id"],
        parent_id=project["root_directory_id"],
        name="operations",
        description=description,
    )
    repository.seed_file(
        project["id"],
        directory_id=operations["id"],
        name=file_name,
        body="# Release recovery\n\nBring the previous release back, then smoke test it.",
    )
    service, _ = _service(repository)

    payload = await _search(service, project, query="rollback plan")

    assert [hit["name"] for hit in payload["results"]] == [file_name]
    assert payload["results"][0]["matched_terms"] == ["plan", "rollback"]
