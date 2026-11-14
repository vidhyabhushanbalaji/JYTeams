"""The document query: name, headings and the most frequent terms, compact enough to score."""

from __future__ import annotations

from app.graph_add.scoring import QUERY_TERM_BUDGET, document_query

BODY = """# Rollback runbook

When a release fails in production, roll back with the previous Helm chart.
The rollback procedure is rehearsed quarterly. Roll back first, then investigate.
"""


def test_the_query_carries_the_title_and_the_file_name() -> None:
    query = document_query(file_name="rollback-runbook.md", text=BODY)

    assert {"rollback", "runbook"} <= query.terms
    assert "rollback" in query.originals.values()


def test_the_query_stays_compact_for_a_long_document() -> None:
    long_body = "# Deploy\n\n" + "\n".join(f"unique{i} release notes" for i in range(500))

    query = document_query(file_name="notes.md", text=long_body)

    assert len(query.terms) <= QUERY_TERM_BUDGET


def test_a_repeated_topic_outweighs_a_one_off_word() -> None:
    text = "# Notes\n\n" + "rollback " * 20 + "trademark"

    query = document_query(file_name="notes.md", text=text)

    assert "rollback" in query.terms and "trademark" in query.terms
    assert query.weight("rollback") >= query.weight("trademark")


def test_markdown_and_stopwords_are_ignored() -> None:
    query = document_query(file_name="a.md", text="# Deploy **the** `helm` chart")

    assert "helm" in query.terms
    assert "the" not in query.terms
