"""The offline searcher: deterministic matching and ranking without a key."""

from __future__ import annotations

from app.core.config import get_settings
from app.graph_ai_search.llm import MockSearcher, build_searcher
from app.graph_ai_search.search import DocumentBrief, FolderBrief, LoggedFile


def _document(file_id: str, name: str, summary: str) -> DocumentBrief:
    return DocumentBrief(
        file_id=file_id,
        name=name,
        path=name,
        directory_id="dir",
        directory_path="",
        summary=summary,
    )


def _folder(
    directory_id: str, name: str, *, description: str = "", contains: tuple[str, ...] = ()
) -> FolderBrief:
    return FolderBrief(
        directory_id=directory_id,
        path=name,
        name=name,
        depth=1,
        description=description or "General material.",
        contains=contains,
    )


async def test_judging_logs_files_whose_summary_matches() -> None:
    searcher = MockSearcher()
    documents = [
        _document("f1", "rollback.md", "Rolling back a failed production release with Helm."),
        _document("f2", "pricing.md", "Pricing tiers and invoicing."),
    ]

    verdicts = await searcher.judge(
        query="how do I roll back a release",
        folder=_folder("root", ""),
        documents=documents,
        folders=[],
    )

    assert [match.file_id for match in verdicts.documents] == ["f1"]
    assert verdicts.documents[0].relevance > 0


async def test_judging_opens_folders_by_description_or_contents() -> None:
    searcher = MockSearcher()
    folders = [
        _folder("guides", "guides", description="Deployment and release procedures."),
        _folder("misc", "misc", description="General material.", contains=("rollback",)),
        _folder("finance", "finance", description="Invoices and pricing."),
    ]

    verdicts = await searcher.judge(
        query="rollback a deployment",
        folder=_folder("root", ""),
        documents=[],
        folders=folders,
    )

    assert {match.directory_id for match in verdicts.folders} == {"guides", "misc"}


async def test_judging_returns_nothing_for_an_unrelated_query() -> None:
    searcher = MockSearcher()

    verdicts = await searcher.judge(
        query="quarterly invoicing",
        folder=_folder("root", ""),
        documents=[_document("f1", "rollback.md", "Rolling back a failed release.")],
        folders=[_folder("guides", "guides", description="Release procedures.")],
    )

    assert verdicts.documents == ()
    assert verdicts.folders == ()


async def test_ranking_orders_the_better_match_first() -> None:
    searcher = MockSearcher()
    documents = [
        LoggedFile(_document("weak", "notes.md", "Some notes about releases."), 0.2),
        LoggedFile(
            _document("strong", "rollback.md", "Rolling back a failed production release."), 0.2
        ),
    ]

    ranked = await searcher.rank(query="roll back a production release", documents=documents)

    assert ranked[0].file_id == "strong"
    assert ranked[0].score > ranked[1].score


def test_without_a_key_the_mock_searcher_is_used() -> None:
    searcher = build_searcher(get_settings())

    assert isinstance(searcher, MockSearcher)
