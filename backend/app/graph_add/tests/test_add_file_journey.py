"""The journey: upload → suggest → place, and the tree stays described with one call."""

from __future__ import annotations

from app.core.config import get_settings
from app.graph_add.schemas import PlacementMode
from app.graph_add.service import GraphAddService
from app.graph_add.tests.fakes import (
    InMemoryAddRepository,
    InMemoryObjectStore,
    ScriptedDescriber,
)

DOCUMENT = b"""# Alert runbook

How to react when the p95 latency alert fires, including when to page the platform team.
"""


def _service(describer: ScriptedDescriber):
    repository = InMemoryAddRepository()
    store = InMemoryObjectStore()
    service = GraphAddService(
        repository=repository,
        store=store,
        describer=describer,
        settings=get_settings(),
    )
    return service, repository


def _seed(repository: InMemoryAddRepository):
    """A three-level tree whose descriptions already describe their folders."""
    project = repository.seed_project()
    root_id = project["root_directory_id"]
    repository.directories[root_id]["description"] = (
        "The project root: onboarding, services and on-call practice."
    )
    repository.seed_file(project["id"], directory_id=root_id, name="README.md")
    operations = repository.seed_directory(
        project["id"],
        parent_id=root_id,
        name="operations",
        description="On-call practice: alerting, monitoring and incident response.",
    )
    runbooks = repository.seed_directory(
        project["id"],
        parent_id=operations["id"],
        name="runbooks",
        description="Step-by-step recovery procedures for specific production alerts.",
    )
    repository.seed_directory(
        project["id"],
        parent_id=root_id,
        name="product",
        description="Roadmap, personas and frequently asked questions.",
    )
    return project, operations, runbooks


async def test_the_whole_journey_keeps_the_tree_described_in_one_call() -> None:
    describer = ScriptedDescriber()
    service, repository = _service(describer)
    project, operations, runbooks = _seed(repository)

    suggestion = await service.suggest(
        owner_id="user-1",
        project_id=project["id"],
        filename="alert-runbook.md",
        data=DOCUMENT,
    )

    # The suggestion step is local: nothing was sent to a model.
    assert describer.calls == []
    offered = [item["path"] for item in suggestion["suggestions"]]
    assert offered[0] == "operations/runbooks"
    assert "operations" in offered
    assert offered[-1] == ""

    result = await service.place(
        owner_id="user-1",
        request_id=suggestion["request_id"],
        directory_id=runbooks["id"],
        placement=PlacementMode.DIRECT,
        new_directory_name=None,
        file_name=None,
    )

    # One model call covered the folder that received the file and its two ancestors.
    assert describer.calls == [("operations/runbooks", "operations", "")]
    assert result["refreshed_directories"] == 3
    assert result["file"]["path"] == "operations/runbooks/alert-runbook.md"

    directories = {row["path"]: row for row in await repository.list_directories(project["id"])}
    assert directories["operations/runbooks"]["direct_file_count"] == 1
    assert "alert-runbook.md" in directories["operations/runbooks"]["description"]
    assert "alert-runbook.md" in directories["operations"]["description"]
    assert "alert-runbook.md" in directories[""]["description"]

    files = await repository.list_files(project["id"])
    placed = next(row for row in files if row["path"].endswith("alert-runbook.md"))
    assert placed["summary_status"] == "skipped"
    assert placed["summary"] is None

    # The updated description is what a later document (or a search) will match.
    second = await service.suggest(
        owner_id="user-1",
        project_id=project["id"],
        filename="latency-alert.md",
        data=b"# Latency alert\n\nWhat to do when the latency alert fires.\n",
    )
    assert second["suggestions"][0]["path"] == "operations/runbooks"


async def test_a_new_folder_created_for_the_document_is_described_too() -> None:
    describer = ScriptedDescriber()
    service, repository = _service(describer)
    project, operations, _ = _seed(repository)

    suggestion = await service.suggest(
        owner_id="user-1",
        project_id=project["id"],
        filename="drills.md",
        data=b"# Incident drills\n\nQuarterly rehearsal of the recovery procedures.\n",
    )

    result = await service.place(
        owner_id="user-1",
        request_id=suggestion["request_id"],
        directory_id=operations["id"],
        placement=PlacementMode.NEW_DIRECTORY,
        new_directory_name="drills",
        file_name=None,
    )

    assert result["created_directory"] is True
    assert result["directory_path"] == "operations/drills"
    assert describer.calls == [("operations/drills", "operations", "")]
    directories = {row["path"]: row for row in await repository.list_directories(project["id"])}
    assert directories["operations/drills"]["description"]
    assert directories["operations"]["child_directory_count"] == 2
