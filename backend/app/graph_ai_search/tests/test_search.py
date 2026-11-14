"""The walk: branch selection, body reads, the optional valve, the read budget and the sweep."""

from __future__ import annotations

from app.core.text import build_query
from app.graph_ai_search.search import (
    DocumentBrief,
    FolderBrief,
    SearchOutcome,
    find_matching_files,
)
from app.graph_ai_search.tests.fakes import ScriptedScorer


def _folder(directory_id: str, path: str, description: str = "") -> FolderBrief:
    return FolderBrief(
        directory_id=directory_id,
        path=path,
        name=path.rsplit("/", 1)[-1] if path else "",
        depth=path.count("/") + 1 if path else 0,
        description=description,
    )


def _document(file_id: str, directory_id: str, directory_path: str, name: str) -> DocumentBrief:
    return DocumentBrief(
        file_id=file_id,
        name=name,
        path=f"{directory_path}/{name}" if directory_path else name,
        directory_id=directory_id,
        directory_path=directory_path,
        storage_bucket="test-bucket",
        storage_path=f"{directory_id}/{name}",
        content_sha256=f"sha-{name}",
    )


class Reader:
    """Records which documents the walk opened, and can fail on demand."""

    def __init__(self, fail: set[str] | None = None) -> None:
        self.reads: list[str] = []
        self.fail = fail or set()

    async def __call__(self, document: DocumentBrief) -> str:
        self.reads.append(document.name)
        if document.name in self.fail:
            raise RuntimeError("bucket unavailable")
        return f"the content of {document.name}"


async def _walk(
    *,
    root: FolderBrief,
    children: dict[str, list[FolderBrief]],
    documents: dict[str, list[DocumentBrief]],
    scorer: ScriptedScorer,
    reader: Reader | None = None,
    **kwargs: object,
) -> tuple[SearchOutcome, Reader]:
    reader = reader or Reader()
    outcome = await find_matching_files(
        root=root,
        documents_of=lambda directory_id: documents.get(directory_id, []),
        children_of=lambda directory_id: children.get(directory_id, []),
        read_body=reader,
        query=build_query("deploy a release"),
        scorer=scorer,
        total_documents=sum(len(items) for items in documents.values()),
        **kwargs,  # type: ignore[arg-type]
    )
    return outcome, reader


def _pulse() -> tuple[FolderBrief, dict[str, list[FolderBrief]], dict[str, list[DocumentBrief]]]:
    """Root with two matching branches and one branch whose description misses."""
    root = _folder("root", "")
    docs = _folder("docs", "docs", "API reference and architecture.")
    guides = _folder("guides", "guides", "Deployment and release procedures.")
    legal = _folder("legal", "legal", "Licences and trademarks.")
    children = {"root": [docs, guides, legal], "docs": [], "guides": [], "legal": []}
    documents = {
        "root": [_document("f-readme", "root", "", "README.md")],
        "docs": [_document("f-arch", "docs", "docs", "architecture.md")],
        "guides": [_document("f-deploy", "guides", "guides", "deployment.md")],
        "legal": [_document("f-licence", "legal", "legal", "licence.md")],
    }
    return root, children, documents


async def test_matching_branches_are_opened_and_their_documents_read() -> None:
    root, children, documents = _pulse()
    scorer = ScriptedScorer(
        folders={"docs": 0.8, "guides": 0.9},
        documents={"deployment.md": 0.9, "architecture.md": 0.5},
    )

    outcome, reader = await _walk(root=root, children=children, documents=documents, scorer=scorer)

    assert outcome.opened == ["", "guides", "docs"]
    # Only the opened branches are read; the pruned branch costs nothing.
    assert sorted(reader.reads) == ["README.md", "architecture.md", "deployment.md"]
    assert [item.document.name for item in outcome.results] == ["deployment.md", "architecture.md"]
    assert outcome.files_read == 3
    assert outcome.fallback_used is False
    assert outcome.scorer_version == "scripted"


async def test_a_branch_below_the_threshold_is_pruned_without_reading_it() -> None:
    root, children, documents = _pulse()
    scorer = ScriptedScorer(folders={"legal": 0.1}, documents={"licence.md": 0.9})

    outcome, reader = await _walk(
        root=root,
        children=children,
        documents=documents,
        scorer=scorer,
        fallback_limit=0,
    )

    assert "legal" not in outcome.opened
    assert "licence.md" not in reader.reads
    assert outcome.results == []


async def test_scores_order_the_results() -> None:
    root = _folder("root", "")
    documents = {
        "root": [
            _document("f1", "root", "", "alpha.md"),
            _document("f2", "root", "", "beta.md"),
            _document("f3", "root", "", "gamma.md"),
        ]
    }
    scorer = ScriptedScorer(documents={"alpha.md": 0.4, "beta.md": 0.85, "gamma.md": 0.6})

    outcome, _ = await _walk(root=root, children={"root": []}, documents=documents, scorer=scorer)

    assert [item.document.name for item in outcome.results] == ["beta.md", "gamma.md", "alpha.md"]
    assert [item.score for item in outcome.results] == [0.85, 0.6, 0.4]


async def test_relevant_folders_are_reported_for_browsing() -> None:
    root, children, documents = _pulse()
    scorer = ScriptedScorer(
        folders={"guides": 0.9, "docs": 0.6},
        matched={"guides": ("deploy", "release")},
    )

    outcome, _ = await _walk(root=root, children=children, documents=documents, scorer=scorer)

    assert [item.path for item in outcome.directories] == ["guides", "docs"]
    assert outcome.directories[0].matched == ("deploy", "release")


async def test_the_optional_valve_stops_the_walk() -> None:
    root, children, documents = _pulse()
    scorer = ScriptedScorer(folders={"docs": 0.8, "guides": 0.9})

    outcome, _ = await _walk(
        root=root, children=children, documents=documents, scorer=scorer, max_directories=1
    )

    assert outcome.budget_exhausted is True
    assert outcome.opened == [""]
    assert outcome.fallback_used is False


async def test_the_read_budget_bounds_a_wide_folder() -> None:
    root = _folder("root", "")
    documents = {
        "root": [_document(f"f{index}", "root", "", f"doc{index}.md") for index in range(10)]
    }
    scorer = ScriptedScorer(documents={f"doc{index}.md": 0.5 for index in range(10)})

    outcome, reader = await _walk(
        root=root, children={"root": []}, documents=documents, scorer=scorer, max_files_read=4
    )

    assert outcome.budget_exhausted is True
    assert len(reader.reads) == 4
    assert outcome.files_read == 4


async def test_an_unreadable_document_degrades_without_losing_the_rest() -> None:
    root = _folder("root", "")
    documents = {
        "root": [
            _document("f1", "root", "", "broken.md"),
            _document("f2", "root", "", "fine.md"),
        ]
    }
    scorer = ScriptedScorer(documents={"broken.md": 0.9, "fine.md": 0.6})
    reader = Reader(fail={"broken.md"})

    outcome, _ = await _walk(
        root=root, children={"root": []}, documents=documents, scorer=scorer, reader=reader
    )

    assert outcome.degraded is True
    assert [item.document.name for item in outcome.results] == ["fine.md"]


async def test_the_sweep_reads_a_branch_the_description_missed() -> None:
    root, children, documents = _pulse()
    # Nothing matches at the root, so "guides" is never opened by the guided walk.
    scorer = ScriptedScorer(documents={"deployment.md": 0.8})

    outcome, reader = await _walk(root=root, children=children, documents=documents, scorer=scorer)

    assert outcome.fallback_used is True
    assert [item.document.name for item in outcome.results] == ["deployment.md"]
    assert "deployment.md" in reader.reads


async def test_the_sweep_is_skipped_for_large_projects() -> None:
    root = _folder("root", "")
    documents = {
        "root": [_document(f"f{index}", "root", "", f"note{index}.md") for index in range(41)]
    }
    scorer = ScriptedScorer()

    outcome, _ = await _walk(root=root, children={"root": []}, documents=documents, scorer=scorer)

    assert outcome.fallback_used is False
    assert outcome.results == []


async def test_a_match_keeps_the_highest_score_seen_for_one_file() -> None:
    root = _folder("root", "")
    document = _document("f1", "root", "", "notes.md")
    scorer = ScriptedScorer(documents={"notes.md": 0.7})

    outcome, _ = await _walk(
        root=root, children={"root": []}, documents={"root": [document]}, scorer=scorer
    )

    assert len(outcome.results) == 1
    assert outcome.results[0].document.file_id == "f1"
    assert outcome.results[0].score == 0.7
