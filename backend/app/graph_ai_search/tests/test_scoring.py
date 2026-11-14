"""The local scorer: tokenising, folder relevance, document relevance, excerpts and caching."""

from __future__ import annotations

from app.core.text import (
    ScoreConfig,
    build_query,
    excerpt,
    score_document_texts,
    score_folder_texts,
    terms,
)
from app.graph_ai_search.scoring import LocalScorer
from app.graph_ai_search.search import DocumentBrief, FolderBrief
from app.graph_ai_search.storage import BlobCache, DocumentTextReader
from app.graph_ai_search.tests.fakes import FakeBlobStore


def test_terms_strip_markdown_and_stopwords_and_stem() -> None:
    assert terms("# Deployment\n\nRoll back the **releases** with `helm`.") == {
        "deploy",
        "roll",
        "back",
        "releas",
        "helm",
    }


def test_a_folder_matches_on_its_description_and_name() -> None:
    query = build_query("deployment release")

    described = score_folder_texts(
        query, name="guides", description="Deployment and release procedures."
    )
    unrelated = score_folder_texts(query, name="legal", description="Licences and trademarks.")

    assert described > 0.5
    assert unrelated == 0.0


def test_a_folder_with_a_colloquial_description_still_matches_on_contains() -> None:
    query = build_query("helm")

    with_names = score_folder_texts(
        query, name="guides", description="Platform material.", contains=("deployment", "helm")
    )
    without_names = score_folder_texts(query, name="guides", description="Platform material.")

    assert with_names > without_names


def test_a_document_is_scored_from_its_body_not_just_its_name() -> None:
    query = build_query("helm rollback")

    body_match = score_document_texts(
        query, name="notes.md", body="Use the previous Helm chart to roll back."
    )
    name_only = score_document_texts(query, name="helm.md", body="Licences and trademarks.")

    assert body_match > name_only > 0


def test_a_phrase_hit_scores_higher_than_scattered_words() -> None:
    query = build_query("roll back a release")

    together = score_document_texts(query, name="a.md", body="Roll back a release carefully.")
    scattered = score_document_texts(
        query, name="b.md", body="Roll the dice. Back to the start. Release the lock."
    )

    assert together > scattered


def test_long_documents_are_not_rewarded_for_length_alone() -> None:
    query = build_query("timescaledb")
    padding = "unrelated sentence about nothing in particular. " * 400

    short = score_document_texts(query, name="a.md", body="Events land in TimescaleDB.")
    long = score_document_texts(query, name="b.md", body=f"{padding}Events land in TimescaleDB.")

    assert short == long


def test_excerpt_shows_context_around_the_match() -> None:
    body = "# Deployment\n\n" + ("filler " * 60) + "roll back a release with the previous chart."

    snippet = excerpt(body, ("release",), width=60)

    assert "release" in snippet
    assert snippet.startswith("…")


def test_query_coverage_is_shared_across_terms() -> None:
    query = build_query("deployment release")

    assert query.coverage(terms("deployment only")) == 0.5
    assert query.coverage(frozenset()) == 0.0


def test_the_scorer_reports_version_and_matched_terms() -> None:
    scorer = LocalScorer(config=ScoreConfig(version="test-1"))
    query = build_query("deployment release")
    folder = FolderBrief(
        directory_id="d1",
        path="guides",
        name="guides",
        depth=1,
        description="Deployment and release procedures.",
        contains=("deployment",),
    )
    document = DocumentBrief(
        file_id="f1",
        name="deployment.md",
        path="guides/deployment.md",
        directory_id="d1",
        directory_path="guides",
    )

    folder_verdict = scorer.score_folder(query, folder)
    document_verdict = scorer.score_document(query, document, "How to deploy a release.")

    assert scorer.version == "test-1"
    assert folder_verdict.matched == ("deployment", "release")
    assert document_verdict.matched == ("deployment", "release")
    assert 0 < document_verdict.score <= 1


async def test_the_reader_caches_by_content_digest() -> None:
    store = FakeBlobStore({"path.md": b"# Title\n\nBody text."})
    reader = DocumentTextReader(store=store, cache=BlobCache(max_entries=4))

    first = await reader.read(bucket="bucket", path="path.md", digest="sha-1")
    second = await reader.read(bucket="bucket", path="path.md", digest="sha-1")

    assert first == second == "# Title\n\nBody text."
    assert store.reads == ["path.md"]  # the second read came from the cache


async def test_the_cache_evicts_the_least_recently_used_entry() -> None:
    cache = BlobCache(max_entries=2)
    cache.put("a", "1")
    cache.put("b", "2")
    cache.get("a")
    cache.put("c", "3")

    assert cache.get("a") == "1"
    assert cache.get("b") is None
    assert cache.get("c") == "3"
