"""The semantic walk: where it stops, how it orders, and what it reports."""

from __future__ import annotations

from collections.abc import Sequence

from app.graph_add.navigate import (
    BUDGET_REASON,
    DEGRADED_REASON,
    NO_MATCH_REASON,
    ChildBrief,
    find_add_locations,
)
from app.graph_add.tests.fakes import ScriptedNavigator


def _folder(directory_id: str, path: str, *, children: int = 0) -> ChildBrief:
    return ChildBrief(
        directory_id=directory_id,
        path=path,
        name=path.rsplit("/", 1)[-1] if path else "",
        depth=path.count("/") + 1 if path else 0,
        description=f"everything about {path or 'the project'}",
        direct_file_count=0,
        child_directory_count=children,
    )


def _lookup(spec: dict[str, list[ChildBrief]]):
    def children_of(directory_id: str) -> Sequence[ChildBrief]:
        return spec.get(directory_id, [])

    return children_of


async def _walk(
    root: ChildBrief,
    spec: dict[str, list[ChildBrief]],
    navigator: ScriptedNavigator,
    *,
    file_name: str = "auth.md",
    **kwargs: object,
):
    return await find_add_locations(
        root=root,
        children_of=_lookup(spec),
        files_of=None,
        summary="how tokens refresh and sessions expire",
        file_name=file_name,
        navigator=navigator,
        **kwargs,  # type: ignore[arg-type]
    )


async def test_walk_descends_the_matching_branch_and_stops_at_the_leaf() -> None:
    root = _folder("root", "", children=1)
    docs = _folder("docs", "docs", children=1)
    api = _folder("api", "docs/api")
    navigator = ScriptedNavigator(matches={"": [("docs", 0.9)], "docs": [("api", 0.85)]})

    traversal = await _walk(root, {"root": [docs], "docs": [api]}, navigator)

    assert [item.node.path for item in traversal.locations] == ["docs/api", ""]
    assert traversal.locations[0].score == 0.85
    assert traversal.locations[0].folder_names == ("auth",)
    assert traversal.expanded == 2
    assert [kind for kind, _ in navigator.calls] == ["judge", "judge"]


async def test_walk_stops_where_no_child_folder_relates() -> None:
    root = _folder("root", "", children=1)
    docs = _folder("docs", "docs", children=1)
    api = _folder("api", "docs/api")
    navigator = ScriptedNavigator(matches={"": [("docs", 0.9)]})

    traversal = await _walk(root, {"root": [docs], "docs": [api]}, navigator)

    assert traversal.locations[0].node.path == "docs"
    assert traversal.locations[0].reason == NO_MATCH_REASON
    assert traversal.expanded == 2


async def test_branch_limit_prunes_the_weakest_matches() -> None:
    root = _folder("root", "", children=3)
    leaves = [_folder(name, name) for name in ("a", "b", "c")]
    navigator = ScriptedNavigator(matches={"": [("a", 0.4), ("b", 0.9), ("c", 0.7)]})

    traversal = await _walk(root, {"root": leaves}, navigator, max_branch=2)

    assert traversal.visited == 3  # root, b and c — "a" was never opened
    assert [item.node.path for item in traversal.locations] == ["b", "c", ""]
    assert traversal.locations[-1].score == 0.0


async def test_budget_exhaustion_is_flagged_on_the_candidate() -> None:
    root = _folder("root", "", children=1)
    one = _folder("one", "one", children=1)
    two = _folder("two", "one/two")
    navigator = ScriptedNavigator(matches={"": [("one", 0.9)], "one": [("two", 0.8)]})

    traversal = await _walk(root, {"root": [one], "one": [two]}, navigator, max_expansions=1)

    assert traversal.budget_exhausted is True
    assert traversal.locations[0].node.path == "one"
    assert traversal.locations[0].reason == BUDGET_REASON
    assert traversal.locations[0].budget_exhausted is True


async def test_failed_matching_degrades_instead_of_failing() -> None:
    root = _folder("root", "", children=1)
    navigator = ScriptedNavigator(fail_judging=True)

    traversal = await _walk(root, {"root": [_folder("a", "a")]}, navigator)

    assert traversal.degraded is True
    assert len(traversal.locations) == 1
    assert traversal.locations[0].node.path == ""
    assert traversal.locations[0].reason == DEGRADED_REASON


async def test_equal_matches_are_ordered_deterministically() -> None:
    root = _folder("root", "", children=2)
    leaves = [_folder("b", "b"), _folder("a", "a")]
    navigator = ScriptedNavigator(matches={"": [("b", 0.6), ("a", 0.6)]})

    traversal = await _walk(root, {"root": leaves}, navigator)

    assert [item.node.path for item in traversal.locations] == ["a", "b", ""]


async def test_an_empty_tree_only_offers_the_root() -> None:
    root = _folder("root", "")
    navigator = ScriptedNavigator()

    traversal = await _walk(root, {}, navigator)

    assert [item.node.path for item in traversal.locations] == [""]
    assert traversal.expanded == 0
    assert navigator.calls == []
