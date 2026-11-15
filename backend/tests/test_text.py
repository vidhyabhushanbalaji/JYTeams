"""The shared text handling: description prose, tokenising and local matching."""

from __future__ import annotations

from app.core.text import (
    build_query,
    clip_description,
    naturalise_description,
    normalise_phrase,
    score_document_texts,
    terms,
)


def test_short_text_is_returned_unchanged() -> None:
    assert clip_description("A short description.", 300) == "A short description."


def test_whitespace_is_collapsed() -> None:
    assert clip_description("  one\n\ntwo   three  ", 300) == "one two three"


def test_long_text_is_cut_at_a_word_boundary_within_the_limit() -> None:
    clipped = clip_description("alpha " * 100, 300)

    assert len(clipped) <= 300
    assert clipped.endswith("…")
    assert clipped[:-1].split()[-1] == "alpha"


def test_the_ellipsis_counts_towards_the_limit() -> None:
    clipped = clip_description("word " * 200, 50)

    assert len(clipped) <= 50
    assert clipped.endswith("…")


def test_a_text_at_the_limit_is_untouched() -> None:
    text = "x" * 300
    assert clip_description(text, 300) == text


def test_a_zero_limit_returns_nothing() -> None:
    assert clip_description("anything", 0) == ""


def test_a_description_loses_hyphens_and_underscores() -> None:
    assert (
        clip_description("Rollback-plan and deploy_run for a failed release.", 300)
        == "Rollback plan and deploy run for a failed release."
    )


def test_naturalising_keeps_every_word_and_the_camel_case_acronyms() -> None:
    assert naturalise_description("OAuth and iOS notes about rollback-plan") == (
        "OAuth and iOS notes about rollback plan"
    )


def test_naturalising_keeps_code_identifiers_and_urls() -> None:
    text = "See `X-RateLimit` and `request_id`, then https://example.com/rollback-plan."

    assert naturalise_description(text) == text


def test_a_hyphenated_name_matches_the_spaced_query() -> None:
    query = build_query("rollback plan")

    assert query.coverage(terms("rollback-plan.md")) == 1.0
    assert query.coverage(terms("rollback_plan.md")) == 1.0
    assert query.coverage(terms("RollbackPlan.md")) == 1.0


def test_the_query_matches_a_hyphenated_body_as_a_phrase() -> None:
    query = build_query("rollback plan")

    score = score_document_texts(
        query, name="notes.md", body="A rollback-plan restores the previous release."
    )

    assert score == 1.0


def test_a_query_without_the_separator_matches_a_compound_name() -> None:
    assert build_query("rollbackplan").coverage(terms("rollback-plan.md")) == 1.0


def test_a_hyphenated_query_still_covers_prose() -> None:
    query = build_query("rollback-plan review")

    assert query.coverage(terms("Rollback plan review for a failed release.")) == 1.0


def test_camel_case_names_are_two_words() -> None:
    assert terms("releaseNotes.md") == terms("release notes.md")


def test_the_phrase_is_normalised_across_separators() -> None:
    assert normalise_phrase("Rollback-Plan") == "rollback plan"
    assert normalise_phrase("releaseNotes") == "release notes"
