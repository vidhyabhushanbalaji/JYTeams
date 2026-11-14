"""The offline navigator: deterministic, and genuinely useful without a key."""

from __future__ import annotations

from app.core.config import get_settings
from app.graph_add.llm import MockNavigator, build_navigator
from app.graph_add.navigate import CandidateContext, ChildBrief


def _folder(directory_id: str, name: str, *, description: str = "", contains=()) -> ChildBrief:
    return ChildBrief(
        directory_id=directory_id,
        path=name,
        name=name,
        depth=1,
        description=description,
        child_directory_count=len(contains),
        contains=tuple(contains),
    )


async def test_summary_keeps_the_document_body() -> None:
    summary = await MockNavigator().summarise_file(
        name="session-expiry.md", text="# Session expiry\n\nHow tokens refresh."
    )

    assert "session-expiry.md" in summary
    assert "tokens refresh" in summary


async def test_judging_matches_on_the_names_a_folder_contains() -> None:
    navigator = MockNavigator()
    auth = _folder(
        "auth",
        "auth",
        description="Authentication and authorization: sessions, tokens, sign-in.",
        contains=("tokens",),
    )
    api = _folder(
        "api", "api", description="HTTP endpoint reference and payloads.", contains=("users",)
    )

    judged = await navigator.judge_children(
        file_name="session-expiry.md",
        summary="Session expiry and token refresh for the authentication service.",
        path="docs",
        children=[auth, api],
    )

    assert [item.directory_id for item in judged] == ["auth"]
    assert judged[0].relevance > 0


async def test_judging_returns_nothing_for_an_unrelated_document() -> None:
    navigator = MockNavigator()

    judged = await navigator.judge_children(
        file_name="pricing.md",
        summary="Quarterly pricing tiers and invoicing.",
        path="docs",
        children=[_folder("auth", "auth", description="Sessions and tokens.")],
    )

    assert judged == []


async def test_ranking_orders_the_better_match_first() -> None:
    navigator = MockNavigator()
    weak = CandidateContext(node=_folder("a", "notes", description="Meeting notes."))
    strong = CandidateContext(
        node=_folder("b", "auth", description="Session expiry and token refresh.")
    )

    ranked = await navigator.rank(
        file_name="session-expiry.md",
        summary="How sessions expire and tokens refresh.",
        candidates=[weak, strong],
    )

    assert [item.directory_id for item in ranked] == ["b", "a"]
    assert ranked[0].folder_names == ("session expiry",)


async def test_describing_a_folder_reports_what_it_holds() -> None:
    description = await MockNavigator().describe_folder(
        path="docs/auth", files=[("tokens.md", "Token refresh.")], directories=[]
    )

    assert "docs/auth" in description
    assert "tokens.md" in description


def test_without_a_key_the_mock_navigator_is_used() -> None:
    navigator = build_navigator(get_settings())

    assert isinstance(navigator, MockNavigator)
