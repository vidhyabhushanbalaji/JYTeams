"""Local folder ranking: thresholds, ordering, the root fallback and determinism."""

from __future__ import annotations

from app.core.text import build_query
from app.graph_add.navigate import ROOT_REASON, ChildBrief, score_folders


def _folder(path: str, description: str = "", **kwargs: object) -> ChildBrief:
    return ChildBrief(
        directory_id=f"dir-{path or 'root'}",
        path=path,
        name=path.rsplit("/", 1)[-1] if path else "",
        depth=path.count("/") + 1 if path else 0,
        description=description,
        **kwargs,  # type: ignore[arg-type]
    )


def _scan(
    folders: list[ChildBrief],
    query: str = "helm rollback release",
    *,
    root_description: str = "The project root.",
    **kwargs: object,
):
    """Score the folders, adding the project root when the caller did not supply one."""
    if all(folder.path != "" for folder in folders):
        folders = [_folder("", root_description), *folders]
    return score_folders(
        folders=folders,
        query=build_query(query),
        file_name="rollback.md",
        root_id="dir-root",
        **kwargs,  # type: ignore[arg-type]
    )


def test_a_matching_folder_is_offered_with_the_matching_terms() -> None:
    guides = _folder("guides", "Deployment and release procedures, including rollback steps.")
    legal = _folder("legal", "Licences and trademarks.")

    scan = _scan([guides, legal])

    assert [item.node.path for item in scan.locations] == ["guides", ""]
    assert scan.locations[0].score > 0.3
    assert "rollback" in scan.locations[0].matched
    assert "rollback" in scan.locations[0].reason


def test_a_folder_below_the_threshold_is_not_offered() -> None:
    legal = _folder("legal", "Licences and trademarks.")

    scan = _scan([legal])

    assert [item.node.path for item in scan.locations] == [""]


def test_scores_order_the_locations() -> None:
    strong = _folder("guides/rollback", "Rolling back a failed helm release.")
    weaker = _folder("guides", "Helm deployment material.")

    scan = _scan([strong, weaker], max_candidates=3)

    assert [item.node.path for item in scan.locations] == ["guides/rollback", "guides", ""]


def test_the_root_is_always_offered_last() -> None:
    scan = _scan([_folder("guides", "Rollbacks.")])

    assert scan.locations[-1].node.path == ""
    assert scan.locations[-1].reason == ROOT_REASON
    assert scan.locations[-1].score == 0.0


def test_the_root_is_not_duplicated_when_it_matches() -> None:
    scan = _scan([_folder("guides", "Rollbacks.")], root_description="Rollback and release notes.")

    paths = [item.node.path for item in scan.locations]

    assert paths.count("") == 1
    assert paths[0] == ""  # it matched, so it is ranked rather than appended


def test_equal_scores_are_ordered_deterministically() -> None:
    first = _folder("b", "Release rollback.")
    second = _folder("a", "Release rollback.")

    scan = _scan([second, first])

    assert [item.node.path for item in scan.locations] == ["a", "b", ""]


def test_max_candidates_trims_the_offer() -> None:
    folders = [_folder(name, "Release rollback.") for name in ("a", "b", "c", "d")]

    scan = _scan(folders, max_candidates=2)

    assert [item.node.path for item in scan.locations] == ["a", "b", ""]


def test_an_empty_tree_only_offers_the_root() -> None:
    scan = _scan([_folder("")])

    assert [item.node.path for item in scan.locations] == [""]
    assert scan.scored == 1
    assert scan.threshold == 0.05
    assert scan.scorer_version


def test_the_scan_is_reported_for_the_wizard() -> None:
    scan = _scan([_folder(""), _folder("guides", "Deployment and release procedures.")])

    assert scan.as_dict() == {
        "folders_scored": 2,
        "threshold": 0.05,
        "scorer_version": scan.scorer_version,
    }
