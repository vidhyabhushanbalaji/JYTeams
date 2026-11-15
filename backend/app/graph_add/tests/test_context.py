"""A ticket's context can steer a placement, without overriding the document itself."""

from __future__ import annotations

from app.graph_add.navigate import ChildBrief, score_folders
from app.graph_add.scoring import context_query, document_query

FOLDERS = [
    ChildBrief(
        directory_id="dir-auth",
        path="pulse/auth",
        name="auth",
        depth=1,
        description="Token authentication and login redirects.",
    ),
    ChildBrief(
        directory_id="dir-release",
        path="pulse/release",
        name="release",
        depth=1,
        description="Deployment runbook and rollback procedure.",
    ),
]


def _scan(*, text: str, context: str = "", file_name: str = "notes.md"):
    return score_folders(
        folders=FOLDERS,
        query=document_query(file_name=file_name, text=text),
        file_name=file_name,
        root_id="dir-root",
        context=context_query(context) if context else None,
    )


def test_an_empty_context_is_no_context() -> None:
    assert context_query("   ") is None


def test_context_does_not_change_a_confident_document_match() -> None:
    text = "# Authentication login\n\nAuthentication login token redirect."

    plain = _scan(text=text, file_name="auth.md")
    hinted = _scan(text=text, file_name="auth.md", context="deployment rollback release procedure")

    assert plain.locations[0].node.directory_id == "dir-auth"
    assert hinted.locations[0].node.directory_id == "dir-auth"
    release = {item.node.directory_id: item.score for item in hinted.locations}
    auth = {item.node.directory_id: item.score for item in hinted.locations}
    assert auth["dir-auth"] > release.get("dir-release", 0.0)


def test_context_lifts_a_folder_the_document_alone_does_not_name() -> None:
    text = "# Notes\n\nGeneral notes about the service."

    plain = _scan(text=text, context="")
    hinted = _scan(text=text, context="deployment rollback release procedure")

    release = {item.node.directory_id: item.score for item in hinted.locations}
    assert release.get("dir-release", 0.0) > 0.0
    assert release["dir-release"] > 0.0
    # The un-hinted scan cannot see the release folder at all.
    assert "dir-release" not in {item.node.directory_id for item in plain.locations}


def test_context_terms_are_reported_as_matched_terms() -> None:
    hinted = _scan(text="# Notes\n\nGeneral notes.", context="rollback deployment")

    release = next(item for item in hinted.locations if item.node.directory_id == "dir-release")
    assert "rollback" in release.matched


def test_the_document_query_itself_is_unchanged() -> None:
    query = document_query(file_name="auth.md", text="# Auth\n\nTokens rotate.")

    assert "auth" in query.terms
    assert "token" in query.terms or "tokens" in query.terms
