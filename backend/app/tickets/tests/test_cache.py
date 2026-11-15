"""The cache helpers: the two fingerprints, and what a ticket searches for without a model."""

from __future__ import annotations

from app.tickets.cache import (
    FILE_LIMIT,
    file_signature,
    fingerprint,
    search_query,
    terms_fingerprint,
)


def _files(*updated_at: str) -> list[dict]:
    return [{"id": f"file-{index}", "updated_at": value} for index, value in enumerate(updated_at)]


def test_file_signature_counts_documents_and_dates_the_newest() -> None:
    assert file_signature(_files("2026-01-01", "2026-02-03", "2026-01-15")) == ("3:2026-02-03")


def test_file_signature_of_an_empty_project() -> None:
    assert file_signature([]) == "0:"


def test_terms_fingerprint_is_stable_for_the_same_wording() -> None:
    first = terms_fingerprint(title="Review decision rights", description="Is it accurate?")
    second = terms_fingerprint(title="Review decision rights", description="Is it accurate?")

    assert first == second
    assert len(first) == 64


def test_terms_fingerprint_changes_when_the_wording_changes() -> None:
    base = terms_fingerprint(title="Review decision rights", description="")

    assert base != terms_fingerprint(title="Review decision rights please", description="")
    assert base != terms_fingerprint(title="Review decision rights", description="Check it.")


def test_terms_fingerprint_ignores_whitespace() -> None:
    assert terms_fingerprint(title="Review   decision rights", description="a  b") == (
        terms_fingerprint(title=" Review decision rights ", description="a b")
    )


def test_terms_fingerprint_changes_when_the_distiller_changes() -> None:
    base = terms_fingerprint(title="Auth", description="tokens")

    assert base != terms_fingerprint(
        title="Auth", description="tokens", distiller_version="distil-0"
    )


def test_fingerprint_is_stable_for_the_same_inputs() -> None:
    files = _files("2026-01-01")
    first = fingerprint(query="auth tokens", files=files, folder_threshold=0.25)
    second = fingerprint(query="auth tokens", files=files, folder_threshold=0.25)

    assert first == second
    assert len(first) == 64


def test_fingerprint_changes_when_the_terms_change() -> None:
    files = _files("2026-01-01")
    base = fingerprint(query="decision rights", files=files, folder_threshold=0.25)

    assert base != fingerprint(query="decision rights accurate", files=files, folder_threshold=0.25)
    assert base != fingerprint(
        query="decision rights",
        context="approval authority",
        files=files,
        folder_threshold=0.25,
    )


def test_fingerprint_changes_when_the_project_changes() -> None:
    base = fingerprint(query="auth", files=_files("2026-01-01"), folder_threshold=0.25)

    assert base != fingerprint(
        query="auth", files=_files("2026-01-01", "2026-01-09"), folder_threshold=0.25
    )
    assert base != fingerprint(query="auth", files=_files("2026-01-05"), folder_threshold=0.25)


def test_fingerprint_changes_when_the_limit_or_threshold_changes() -> None:
    files = _files("2026-01-01")
    base = fingerprint(query="auth", files=files, folder_threshold=0.25)

    assert base != fingerprint(
        query="auth", files=files, limit=FILE_LIMIT + 1, folder_threshold=0.25
    )
    assert base != fingerprint(query="auth", files=files, folder_threshold=0.4)


def test_fingerprint_changes_when_the_matcher_or_distiller_changes() -> None:
    files = _files("2026-01-01")
    base = fingerprint(query="auth", files=files, folder_threshold=0.25)

    assert base != fingerprint(
        query="auth",
        files=files,
        folder_threshold=0.25,
        matching_version="local-1",
    )
    assert base != fingerprint(
        query="auth",
        files=files,
        folder_threshold=0.25,
        distiller_version="distil-0",
    )


def test_whitespace_does_not_change_the_fingerprint() -> None:
    files = _files("2026-01-01")

    assert fingerprint(
        query="auth  tokens", context="is  it", files=files, folder_threshold=0.25
    ) == fingerprint(query=" auth tokens ", context="is it", files=files, folder_threshold=0.25)


def test_search_query_uses_the_title_and_the_description_as_context() -> None:
    query, context, reason = search_query("Fix login", "The token endpoint rejects rotation.")

    assert query == "Fix login"
    assert context == "The token endpoint rejects rotation."
    assert reason is None


def test_a_short_title_falls_back_to_the_description() -> None:
    query, context, reason = search_query("UI", "The settings dialog overflows on small screens.")

    assert query.startswith("The settings dialog")
    assert context.startswith("The settings dialog")
    assert reason is None


def test_a_ticket_with_nothing_to_search_explains_itself() -> None:
    query, context, reason = search_query("UI", "ok")

    assert query == ""
    assert context == "ok"
    assert reason is not None


def test_context_is_trimmed_to_the_search_endpoint_cap() -> None:
    _, context, _ = search_query("Fix login", "word " * 500)

    assert len(context) <= 500
