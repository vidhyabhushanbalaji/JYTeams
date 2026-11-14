"""The walk: exhaustive descent, the optional valve, the fallback and batching."""

from __future__ import annotations

from app.graph_ai_search.search import (
    DocumentBrief,
    FolderBrief,
    SearchOutcome,
    find_matching_files,
)
from app.graph_ai_search.tests.fakes import ScriptedSearcher


def _folder(directory_id: str, path: str, *, description: str = "") -> FolderBrief:
    return FolderBrief(
        directory_id=directory_id,
        path=path,
        name=path.rsplit("/", 1)[-1] if path else "",
        depth=path.count("/") + 1 if path else 0,
        description=description or f"everything about {path or 'the project'}",
    )


def _document(file_id: str, directory_path: str, name: str, summary: str = "") -> DocumentBrief:
    return DocumentBrief(
        file_id=file_id,
        name=name,
        path=f"{directory_path}/{name}" if directory_path else name,
        directory_id=f"dir-of-{directory_path or 'root'}",
        directory_path=directory_path,
        summary=summary or f"about {name}",
    )


async def _walk(
    root: FolderBrief,
    folders: dict[str, list[FolderBrief]],
    documents: dict[str, list[DocumentBrief]],
    searcher: ScriptedSearcher,
    *,
    query: str = "rollback a deployment",
    **kwargs: object,
) -> SearchOutcome:
    return await find_matching_files(
        root=root,
        documents_of=lambda directory_id: documents.get(directory_id, []),
        children_of=lambda directory_id: folders.get(directory_id, []),
        query=query,
        searcher=searcher,
        total_documents=sum(len(items) for items in documents.values()),
        **kwargs,  # type: ignore[arg-type]
    )


async def test_walk_exhausts_every_matching_branch() -> None:
    """Twelve matching folders in a chain: more than any former budget, all must open."""
    depth = 12
    chain = [_folder(f"d{index}", f"level{index}") for index in range(depth)]
    root = _folder("root", "")
    folders = {"root": [chain[0]]}
    matches: dict[str, dict[str, list[str]]] = {"": {"folders": [chain[0].name]}}
    for index in range(depth - 1):
        folders[f"d{index}"] = [chain[index + 1]]
        matches[chain[index].path] = {"folders": [chain[index + 1].name]}
    matches[chain[-1].path] = {"files": ["deep.md"]}

    documents = {chain[-1].directory_id: [_document("f-deep", chain[-1].path, "deep.md")]}
    searcher = ScriptedSearcher(matches=matches)

    outcome = await _walk(root, folders, documents, searcher)

    assert outcome.budget_exhausted is False
    assert len(outcome.opened) == depth + 1  # the root plus every level
    assert [item.document.name for item in outcome.results] == ["deep.md"]


async def test_all_matching_children_are_opened() -> None:
    """Six matching siblings: there is no per-node branch limit."""
    root = _folder("root", "")
    children = [_folder(f"c{index}", f"topic{index}") for index in range(6)]
    folders = {"root": children}
    for child in children:
        folders[child.directory_id] = []
    documents = {
        child.directory_id: [_document(f"f{child.directory_id}", child.path, "notes.md")]
        for child in children
    }
    searcher = ScriptedSearcher(
        matches={
            "": {"folders": [child.name for child in children]},
            **{child.path: {"files": ["notes.md"]} for child in children},
        }
    )

    outcome = await _walk(root, folders, documents, searcher)

    assert len(outcome.opened) == 7  # root + six children
    assert len(outcome.results) == 6


async def test_optional_valve_stops_the_walk() -> None:
    """``max_directories`` is the only cap, and it is opt-in."""
    depth = 5
    chain = [_folder(f"d{index}", f"level{index}") for index in range(depth)]
    root = _folder("root", "")
    folders = {"root": [chain[0]]}
    matches: dict[str, dict[str, list[str]]] = {"": {"folders": [chain[0].name]}}
    for index in range(depth - 1):
        folders[f"d{index}"] = [chain[index + 1]]
        matches[chain[index].path] = {"folders": [chain[index + 1].name]}

    outcome = await _walk(root, folders, {}, ScriptedSearcher(matches=matches), max_directories=2)

    assert outcome.budget_exhausted is True
    assert len(outcome.opened) == 2


async def test_the_valve_also_disables_the_fallback() -> None:
    """A bounded walk must not turn into an unbounded sweep."""
    root = _folder("root", "")
    docs = _folder("docs", "docs", description="General material.")
    folders = {"root": [docs], "docs": []}
    documents = {"docs": [_document("f1", "docs", "architecture.md")]}
    searcher = ScriptedSearcher(
        matches={"": {"folders": ["docs"]}, "docs": {"files": ["architecture.md"]}}
    )

    outcome = await _walk(root, folders, documents, searcher, max_directories=1)

    assert outcome.budget_exhausted is True
    assert outcome.fallback_used is False
    assert outcome.opened == [""]


async def test_small_project_fallback_sweeps_the_tree() -> None:
    """A vague folder description must not hide its files on a small project."""
    root = _folder("root", "")
    docs = _folder("docs", "docs", description="General material.")
    folders = {"root": [docs], "docs": []}
    documents = {
        "root": [_document("f-readme", "", "README.md", "Project overview.")],
        "docs": [_document("f-arch", "docs", "architecture.md", "Ingest pipeline design.")],
    }
    # Nothing matches at the root, so "docs" is never opened by the guided walk.
    searcher = ScriptedSearcher(matches={"docs": {"files": ["architecture.md"]}})

    outcome = await _walk(root, folders, documents, searcher)

    assert outcome.fallback_used is True
    assert [item.document.name for item in outcome.results] == ["architecture.md"]
    assert ("judge", "docs") in searcher.calls


async def test_fallback_is_skipped_for_large_projects() -> None:
    root = _folder("root", "")
    documents = {"root": [_document(f"f{index}", "", f"note{index}.md") for index in range(41)]}
    searcher = ScriptedSearcher()

    outcome = await _walk(root, {"root": []}, documents, searcher)

    assert outcome.fallback_used is False
    assert outcome.results == []


async def test_ranking_batches_without_dropping_what_a_caller_can_ask_for() -> None:
    """45 logged files -> two batch calls plus one consolidation of the winners.

    The consolidation covers ``RANK_BATCH`` documents, which is at least the maximum
    ``limit``, so trimming to ``limit`` never loses a document that was worth ranking.
    """
    root = _folder("root", "")
    documents = {
        "root": [_document(f"f{index:02d}", "", f"doc{index:02d}.md") for index in range(45)]
    }
    matches = {"": {"files": [item.name for item in documents["root"]]}}
    searcher = ScriptedSearcher(matches=matches)

    outcome = await _walk(root, {"root": []}, documents, searcher)

    rank_calls = [call for call in searcher.calls if call[0] == "rank"]
    assert len(rank_calls) == 3  # 25 + 20, then the winners
    assert [len(batch) for batch in searcher.ranked_batches] == [25, 20, 25]
    assert outcome.results[0].document.name == "doc00.md"
    assert len({item.document.file_id for item in outcome.results}) == 25


async def test_a_failed_judgement_degrades_instead_of_failing() -> None:
    root = _folder("root", "")
    docs = _folder("docs", "docs")
    documents = {"docs": [_document("f1", "docs", "anything.md")]}

    outcome = await _walk(
        root, {"root": [docs], "docs": []}, documents, ScriptedSearcher(fail_judging=True)
    )

    assert outcome.degraded is True
    assert outcome.results == []


async def test_a_failed_ranking_falls_back_to_relevance() -> None:
    root = _folder("root", "")
    documents = {"root": [_document("f1", "", "notes.md")]}
    searcher = ScriptedSearcher(matches={"": {"files": ["notes.md"]}}, fail_ranking=True)

    outcome = await _walk(root, {"root": []}, documents, searcher)

    assert outcome.degraded is True
    assert [item.document.name for item in outcome.results] == ["notes.md"]
    assert outcome.results[0].score > 0
