#!/usr/bin/env python3
# ruff: noqa: E402 - the executable path bootstrap below must run before the ``app`` imports.
"""Executable end-to-end check of the Graph Add routes ("add a document to a tree").

Run from ``backend/``:

    ../.venv/bin/python -m app.graph_add.tools.verify_add_document
    ../.venv/bin/python app/graph_add/tools/verify_add_document.py --json
    ./app/graph_add/tools/verify_add_document.py          # after chmod +x, with the venv active

It starts the real application in-process (``create_app`` + the actual routers), seeds a
project tree that already holds files, and drives ``POST /suggestions`` →
``POST /placements`` → ``GET /suggestions/{id}`` over HTTP. Every step is asserted, so the
exit code is the result: 0 when all checks pass, 1 otherwise.

No services are touched: the section's in-memory repository and object store stand in for
Supabase, and the offline ``MockFolderDescriber`` replaces the model — the same collaborators the
test suite uses. That makes this a runnable smoke test on a machine with no ``.env``, and a
readable demo of the contract (``--json`` dumps the payloads and the final tree).

For a live run against a real project use ``app.graph_add.tools.add_file`` instead.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from typing import Any

# Executing this file directly puts its own directory on sys.path; add backend/ so
# ``import app`` resolves exactly as it does for
# ``python -m app.graph_add.tools.verify_add_document``.
if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.graph_add.describer import MockFolderDescriber
from app.graph_add.router import get_service
from app.graph_add.service import GraphAddService
from app.graph_add.tests.fakes import InMemoryAddRepository, InMemoryObjectStore
from app.main import create_app

Row = dict[str, Any]

SUGGEST = "/api/graph-add/suggestions"
PLACE = "/api/graph-add/placements"

SESSION = b"# Session expiry\n\nHow sessions expire and how the token refresh flow works."
TOKENS = b"# Tokens\n\nHow authentication tokens are refreshed."
RELEASE = b"# Release process\n\nCutting a release, tagging it and announcing it to the team."

RESPONSE_KEYS = {
    "request_id",
    "project_id",
    "status",
    "expires_at",
    "file",
    "suggestions",
    "scan",
}
SUGGESTION_KEYS = {
    "rank",
    "score",
    "directory_id",
    "path",
    "name",
    "depth",
    "description",
    "direct_file_count",
    "child_directory_count",
    "is_leaf",
    "reason",
    "matched_terms",
    "proposed_new_directory_names",
    "name_available",
    "suggested_file_names",
    "identical_content_at",
}


class Report:
    """Collects PASS/FAIL lines and decides the process exit code."""

    def __init__(self) -> None:
        self.passed = 0
        self.failures: list[str] = []

    def check(self, name: str, condition: bool, detail: object = None) -> bool:
        if condition:
            self.passed += 1
            print(f"  ok    {name}")
            return True
        self.failures.append(name)
        print(f"  FAIL  {name}")
        if detail is not None:
            print(f"        got: {detail}")
        return False

    def summary(self) -> None:
        total = self.passed + len(self.failures)
        if not self.failures:
            print(f"\nall {total} checks passed")
            return
        print(f"\n{self.passed}/{total} checks passed, {len(self.failures)} failed:")
        for name in self.failures:
            print(f"  - {name}")


def seed(repository: InMemoryAddRepository, owner_id: str) -> SimpleNamespace:
    """``root → docs → {guides, api, auth}`` with files already in place."""
    project = repository.seed_project(owner_id=owner_id)
    root_id = project["root_directory_id"]
    repository.seed_file(
        project["id"], directory_id=root_id, name="README.md", summary="Project overview."
    )
    docs = repository.seed_directory(
        project["id"],
        parent_id=root_id,
        name="docs",
        description=(
            "Team guides and how-to articles, including authentication, session handling "
            "and the HTTP API reference."
        ),
    )
    guides = repository.seed_directory(
        project["id"],
        parent_id=docs["id"],
        name="guides",
        description="Step-by-step how-to articles.",
    )
    api = repository.seed_directory(
        project["id"],
        parent_id=docs["id"],
        name="api",
        description="HTTP endpoint reference and payloads.",
    )
    auth = repository.seed_directory(
        project["id"],
        parent_id=docs["id"],
        name="auth",
        description="Authentication and authorization: tokens, sessions, sign-in flows.",
    )
    repository.seed_file(
        project["id"], directory_id=guides["id"], name="release.md", summary="Release checklist."
    )
    repository.seed_file(
        project["id"], directory_id=api["id"], name="users.md", summary="User endpoints."
    )
    repository.seed_file(
        project["id"], directory_id=api["id"], name="errors.md", summary="Error codes."
    )
    repository.seed_file(
        project["id"],
        directory_id=auth["id"],
        name="tokens.md",
        summary="Token refresh and expiry.",
    )
    return SimpleNamespace(
        project=project,
        root_id=root_id,
        docs=docs,
        guides=guides,
        api=api,
        auth=auth,
    )


def build_client(repository: InMemoryAddRepository) -> TestClient:
    """The real app, wired to the in-memory collaborators."""
    service = GraphAddService(
        repository=repository,
        store=InMemoryObjectStore(),
        describer=MockFolderDescriber(),
        settings=get_settings(),
    )
    application = create_app()
    application.dependency_overrides[get_service] = lambda: service
    return TestClient(application)


def suggest(http: TestClient, project_id: str, filename: str, data: bytes):
    return http.post(
        SUGGEST,
        data={"project_id": project_id},
        files={"file": (filename, data, "text/markdown")},
    )


def place(http: TestClient, request_id: str, directory_id: str, **extra: Any):
    return http.post(PLACE, json={"request_id": request_id, "directory_id": directory_id, **extra})


def directories(repository: InMemoryAddRepository, project_id: str) -> dict[str, Row]:
    return {
        row["path"]: row
        for row in repository.directories.values()
        if row["project_id"] == project_id
    }


def files(repository: InMemoryAddRepository, project_id: str) -> dict[str, Row]:
    return {
        row["path"]: row for row in repository.files.values() if row["project_id"] == project_id
    }


def check_suggestions(
    http: TestClient, tree: SimpleNamespace, report: Report, payloads: dict[str, Any]
) -> dict:
    """1. The walk suggests where the document belongs."""
    print("\n1. suggest: where does a new document belong?")
    response = suggest(http, tree.project["id"], "session-expiry.md", SESSION)
    if not report.check(
        "POST /suggestions returns 200", response.status_code == 200, response.text[:300]
    ):
        return {}

    payload = response.json()
    payloads["suggestions"] = payload
    report.check(
        "the response has the documented keys",
        set(payload) == RESPONSE_KEYS,
        sorted(set(payload) ^ RESPONSE_KEYS),
    )
    report.check(
        "every suggestion has the documented keys",
        all(set(item) == SUGGESTION_KEYS for item in payload["suggestions"]),
    )
    paths = [item["path"] for item in payload["suggestions"]]
    report.check("the scan lands on docs/auth", paths[0] == "docs/auth", paths)
    report.check("the project root is offered last", paths[-1] == "", paths)
    report.check(
        "ranks run 1..n",
        [item["rank"] for item in payload["suggestions"]] == list(range(1, len(paths) + 1)),
    )
    report.check(
        "the scan reports what it cost, without a model call",
        payload["scan"]["folders_scored"] >= 1 and bool(payload["scan"]["scorer_version"]),
        payload["scan"],
    )
    report.check("the document preview is returned", bool(payload["file"]["preview"]))
    return payload


def check_replay(
    http: TestClient, suggestion: dict, report: Report, payloads: dict[str, Any]
) -> None:
    """2. The suggestions can be read back without re-uploading."""
    print("\n2. read back: the suggestion the user was shown")
    response = http.get(f"{SUGGEST}/{suggestion['request_id']}")
    if not report.check(
        "GET /suggestions/{id} returns 200", response.status_code == 200, response.text[:200]
    ):
        return
    body = response.json()
    payloads["replay"] = body
    report.check(
        "it replays the same suggestions", body["suggestions"] == suggestion["suggestions"]
    )
    report.check("it still reports the document", body["file"]["name"] == "session-expiry.md")


def check_direct(
    http: TestClient,
    repository: InMemoryAddRepository,
    tree: SimpleNamespace,
    suggestion: dict,
    report: Report,
    payloads: dict[str, Any],
) -> None:
    """3. The file lands in the chosen folder, and the tree is re-described."""
    print("\n3. place: add the file to the suggested folder")
    top = suggestion["suggestions"][0]
    response = place(http, suggestion["request_id"], top["directory_id"])
    if not report.check(
        "POST /placements returns 201", response.status_code == 201, response.text[:300]
    ):
        return

    body = response.json()
    payloads["placement_direct"] = body
    report.check(
        "the file path is docs/auth/session-expiry.md",
        body["file"]["path"] == "docs/auth/session-expiry.md",
        body["file"]["path"],
    )
    report.check("no folder was created", body["created_directory"] is False)
    report.check(
        "three descriptions were refreshed (folder, docs, root)",
        body["refreshed_directories"] == 3,
        body["refreshed_directories"],
    )
    report.check(
        "the blob is stored content-addressed",
        body["file"]["storage_path"].startswith(f"{tree.project['id']}/")
        and body["file"]["storage_path"].endswith(".md"),
        body["file"]["storage_path"],
    )

    tree_dirs = directories(repository, tree.project["id"])
    report.check(
        "the folder's count and description include the file",
        tree_dirs["docs/auth"]["direct_file_count"] == 2
        and "session-expiry.md" in (tree_dirs["docs/auth"]["description"] or ""),
        tree_dirs["docs/auth"]["description"],
    )
    report.check(
        "the refresh reached the root and the project description",
        "docs" in (tree_dirs[""]["description"] or "")
        and repository.projects[tree.project["id"]]["description"] == tree_dirs[""]["description"],
    )


def check_new_folder(
    http: TestClient,
    repository: InMemoryAddRepository,
    tree: SimpleNamespace,
    report: Report,
    payloads: dict[str, Any],
) -> None:
    """5. A new folder at the chosen point, described from its one file."""
    print("\n5. place: create a folder at that point")
    suggestion = suggest(http, tree.project["id"], "release-process.md", RELEASE).json()
    response = place(
        http,
        suggestion["request_id"],
        tree.guides["id"],
        placement="new_directory",
        new_directory_name="release process",
    )
    if not report.check(
        "POST /placements returns 201", response.status_code == 201, response.text[:300]
    ):
        return

    body = response.json()
    payloads["placement_new_folder"] = body
    report.check(
        "the folder path is docs/guides/release process",
        body["directory_path"] == "docs/guides/release process",
        body["directory_path"],
    )
    report.check(
        "the file sits inside the new folder",
        body["file"]["path"] == "docs/guides/release process/release-process.md",
        body["file"]["path"],
    )
    report.check("a folder was created", body["created_directory"] is True)

    tree_dirs = directories(repository, tree.project["id"])
    created = tree_dirs["docs/guides/release process"]
    report.check(
        "depth and ltree path follow the tree rules",
        created["depth"] == 3 and created["ltree_path"] == "docs.guides.release_process",
        (created["depth"], created["ltree_path"]),
    )
    report.check(
        "the folder is described from its file",
        "release-process.md" in (created["description"] or ""),
        created["description"],
    )
    report.check(
        "the parent counts the new subfolder",
        tree_dirs["docs/guides"]["child_directory_count"] == 1,
        tree_dirs["docs/guides"]["child_directory_count"],
    )


def check_clash(
    http: TestClient,
    tree: SimpleNamespace,
    report: Report,
    payloads: dict[str, Any],
) -> None:
    """4. A taken name is reported with alternatives, then resolved by renaming."""
    print("\n4. conflict: the name is taken, rename instead")
    suggestion = suggest(http, tree.project["id"], "tokens.md", TOKENS).json()
    top = suggestion["suggestions"][0]
    payloads["suggestions_clash"] = suggestion
    report.check(
        "the clash is advertised before committing",
        top["path"] == "docs/auth" and top["name_available"] is False,
        (top["path"], top["name_available"]),
    )
    report.check(
        "free names are offered",
        top["suggested_file_names"][:1] == ["tokens-2.md"],
        top["suggested_file_names"],
    )

    conflict = place(http, suggestion["request_id"], top["directory_id"])
    report.check("the placement is refused with 409", conflict.status_code == 409)
    detail = conflict.json().get("detail", {})
    payloads["conflict"] = detail
    report.check(
        "the conflict names the existing file",
        detail.get("conflict", {}).get("path") == "docs/auth/tokens.md",
        detail,
    )
    report.check(
        "the conflict offers alternatives",
        detail.get("suggested_names", [])[:1] == ["tokens-2.md"],
        detail.get("suggested_names"),
    )

    renamed = place(http, suggestion["request_id"], top["directory_id"], file_name="tokens-2.md")
    report.check(
        "the same request places after a rename",
        renamed.status_code == 201 and renamed.json()["file"]["path"] == "docs/auth/tokens-2.md",
        renamed.text[:200],
    )


def check_single_use(
    http: TestClient,
    repository: InMemoryAddRepository,
    tree: SimpleNamespace,
    report: Report,
    payloads: dict[str, Any],
) -> None:
    """6. Identical bytes may live twice; one suggestion may only be used once."""
    print("\n6. duplicates and replays")
    suggestion = suggest(http, tree.project["id"], "session-expiry.md", SESSION).json()
    flag = next((item for item in suggestion["suggestions"] if item["identical_content_at"]), None)
    payloads["suggestions_duplicate"] = suggestion
    report.check(
        "identical content is reported, not blocked",
        flag is not None and flag["identical_content_at"] == ["docs/auth/session-expiry.md"],
        suggestion["suggestions"][0]["identical_content_at"],
    )

    first = place(
        http, suggestion["request_id"], tree.docs["id"], file_name="session-expiry-copy.md"
    )
    report.check(
        "the same bytes can live at a second path",
        first.status_code == 201 and first.json()["file"]["path"] == "docs/session-expiry-copy.md",
        first.text[:200],
    )

    tree_files = files(repository, tree.project["id"])
    report.check(
        "both rows share one blob",
        tree_files["docs/auth/session-expiry.md"]["storage_path"]
        == tree_files["docs/session-expiry-copy.md"]["storage_path"],
    )

    again = place(http, suggestion["request_id"], tree.docs["id"], file_name="third.md")
    report.check("replaying the request is refused with 409", again.status_code == 409)
    detail = again.json().get("detail", {})
    report.check(
        "the refusal names the file it already wrote",
        detail.get("file_id") == first.json()["file"]["id"],
        detail,
    )


def check_expiry(
    http: TestClient,
    repository: InMemoryAddRepository,
    tree: SimpleNamespace,
    report: Report,
) -> None:
    """7. A suggestion past its expiry is refused and marked."""
    print("\n7. expiry: a stale suggestion is refused")
    suggestion = suggest(http, tree.project["id"], "session-cap.md", SESSION).json()
    repository.requests[suggestion["request_id"]]["expires_at"] = (
        datetime.now(UTC) - timedelta(minutes=1)
    ).isoformat()

    response = place(http, suggestion["request_id"], tree.auth["id"], file_name="session-cap.md")
    report.check(
        "the placement is refused with 410", response.status_code == 410, response.status_code
    )
    report.check(
        "the row is marked expired",
        repository.requests[suggestion["request_id"]]["status"] == "expired",
    )


def check_nothing_written(
    http: TestClient,
    repository: InMemoryAddRepository,
    tree: SimpleNamespace,
    report: Report,
) -> None:
    """8. A rejected placement must not leave a folder behind."""
    print("\n8. rejection: nothing is written")
    before = (
        len(directories(repository, tree.project["id"])),
        len(files(repository, tree.project["id"])),
    )
    suggestion = suggest(
        http, tree.project["id"], "index.md", b"# Index\n\nAn index of the guides."
    ).json()

    response = place(
        http,
        suggestion["request_id"],
        tree.docs["id"],
        placement="new_directory",
        new_directory_name="auth",
    )
    report.check(
        "a clashing folder name is refused with 409",
        response.status_code == 409,
        response.status_code,
    )

    after = (
        len(directories(repository, tree.project["id"])),
        len(files(repository, tree.project["id"])),
    )
    report.check("no directory or file rows were added", after == before, f"{before} -> {after}")


def check_foreign(http: TestClient, repository: InMemoryAddRepository, report: Report) -> None:
    """9. Another user's project is invisible."""
    print("\n9. ownership: another user's project is invisible")
    foreign = repository.seed_project(owner_id="someone-else")

    response = suggest(http, foreign["id"], "index.md", b"# Index\n\nAn index of the guides.")
    report.check(
        "suggesting into it returns 404", response.status_code == 404, response.status_code
    )


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    args = build_parser().parse_args(argv)

    # Keep the report readable: the dev-auth warning and one log line per HTTP call
    # are useful in a server, not in a check that makes a dozen calls.
    logging.getLogger("httpx2").setLevel(logging.WARNING)
    logging.getLogger("app.core.auth").setLevel(logging.ERROR)

    settings = get_settings()
    if settings.auth_mode != "dev":
        print(
            "This check identifies itself with the dev user, so it needs AUTH_MODE=dev.\n"
            "For a live run against a real project use app.graph_add.tools.add_file."
        )
        return 2

    print("Graph Add — add-a-document route check")
    print("in-process: real routers, in-memory repository, offline navigator")
    print("seeded tree: root -> docs -> {guides, api, auth}, five files already in place")

    repository = InMemoryAddRepository()
    tree = seed(repository, settings.dev_user_id)
    report = Report()
    payloads: dict[str, Any] = {}

    with build_client(repository) as http:
        suggestion = check_suggestions(http, tree, report, payloads)
        if suggestion:
            check_replay(http, suggestion, report, payloads)
            check_direct(http, repository, tree, suggestion, report, payloads)
        # The clash runs early, while the tree still describes itself richly: it is the
        # only other check that relies on the walk finding docs/auth by itself.
        check_clash(http, tree, report, payloads)
        check_new_folder(http, repository, tree, report, payloads)
        check_single_use(http, repository, tree, report, payloads)
        check_expiry(http, repository, tree, report)
        check_nothing_written(http, repository, tree, report)
        check_foreign(http, repository, report)

    report.summary()

    if args.json:
        print(
            json.dumps(
                {
                    "payloads": payloads,
                    "directories": sorted(directories(repository, tree.project["id"])),
                    "files": sorted(files(repository, tree.project["id"])),
                },
                indent=2,
                default=str,
            )
        )

    return 0 if not report.failures else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="also print the payloads and the final tree as JSON",
    )
    return parser


if __name__ == "__main__":
    sys.exit(main())
