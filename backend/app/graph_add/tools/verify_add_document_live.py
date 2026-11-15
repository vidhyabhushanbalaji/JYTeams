#!/usr/bin/env python3
# ruff: noqa: E402 - the executable path bootstrap below must run before the ``app`` imports.
"""Live check: add one document to a real project, through the real routes.

Run from ``backend/`` (needs a configured ``.env`` — Supabase + a model key):

    ../.venv/bin/python -m app.graph_add.tools.verify_add_document_live \
        --project-id <uuid> --user <owner-uuid> --document path/to/doc.md

    # only look at the suggestions, write nothing
    ... --suggest-only

    # place into a specific folder instead of the top suggestion
    ... --directory guides

The app is started in-process, so the calls go through the real routers and the real
collaborators: the Supabase repository, Supabase Storage and the configured describer. Unlike
``verify_add_document`` (in-memory, no network) this **writes to a real project** — one
``files`` row, one Storage object (content-addressed, so a duplicate document adds none),
and re-described folders up to the root: every ancestor description and the project
description are rewritten, and those model calls are billed.

Exit codes: 0 placed (or, with ``--suggest-only``, suggestions produced), 1 a check failed,
2 the name is taken (the alternatives are printed), 3 nothing to place.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import httpx2

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.graph_add.extract import MARKDOWN_SUFFIXES
from app.graph_add.tools.verify_add_document import Report
from app.main import create_app

Row = dict[str, Any]

SUGGEST = "/api/graph-add/suggestions"
PLACE = "/api/graph-add/placements"
CREATION = "/api/graph-creation"

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


def build_client(args: argparse.Namespace) -> TestClient:
    """The real app. Model calls take seconds, so the transport timeout is generous."""
    client = TestClient(create_app())
    client.timeout = httpx2.Timeout(args.timeout)
    if args.token:
        client.headers["Authorization"] = f"Bearer {args.token}"
    else:
        client.headers["X-Dev-User-Id"] = args.user
    return client


def directories(node: Row):
    """Yield every directory row of a tree response, depth first."""
    yield node
    for child in node.get("directories", []):
        yield from directories(child)


def files(node: Row):
    """Yield every file row of a tree response."""
    yield from node.get("files", [])
    for child in node.get("directories", []):
        yield from files(child)


def find_directory(client: TestClient, project_id: str, wanted: str, *, depth: int) -> Row | None:
    """Locate a directory by id or project-relative path in the live tree."""
    tree = client.get(f"{CREATION}/projects/{project_id}/tree", params={"depth": depth}).json()
    for row in directories(tree["tree"]):
        if row["id"] == wanted or row["path"] == wanted:
            return row
    return None


def print_suggestions(payload: Row) -> None:
    brief = payload["file"]
    print(f"\n  document : {brief['name']} ({brief['size_bytes']} bytes)")
    print(f"  preview  : {brief['preview']}")
    print(f"\n  {'#':>2}  {'score':>5}  {'path':<28}  {'files/dirs':>10}  leaf  reason")
    for item in payload["suggestions"]:
        counts = f"{item['direct_file_count']}/{item['child_directory_count']}"
        leaf = "yes" if item["is_leaf"] else "no"
        path = item["path"] or "(project root)"
        print(
            f"  {item['rank']:>2}  {item['score']:>5.2f}  {path:<28}  {counts:>10}  "
            f"{leaf:<4}  {item['reason']}"
        )
        if not item["name_available"]:
            names = ", ".join(item["suggested_file_names"]) or "(none)"
            print(f"        '{brief['name']}' is taken there; alternatives: {names}")
        if item["identical_content_at"]:
            print(
                f"        identical content already at: {', '.join(item['identical_content_at'])}"
            )
    scan = payload["scan"]
    print(
        f"\n  scan: folders_scored={scan['folders_scored']} threshold={scan['threshold']} "
        f"scorer={scan['scorer_version']} (no model call)"
    )


def run(args: argparse.Namespace, document: Path, report: Report, payloads: dict[str, Any]) -> int:
    settings = get_settings()
    provider = settings.resolved_summarizer
    model = (
        settings.groq_model
        if provider == "groq"
        else settings.gemini_model
        if provider == "gemini"
        else "offline mock"
    )

    print(f"Graph Add — live check against project {args.project_id}")
    print(f"  api          : in-process ({settings.supabase_url or 'SUPABASE_URL missing'})")
    print(f"  storage      : bucket {settings.storage_bucket}")
    print(f"  describer    : {provider} ({model})")
    print(f"  identity     : {'bearer token' if args.token else 'X-Dev-User-Id ' + args.user}")
    print(f"  document     : {document}")

    with build_client(args) as client:
        project = client.get(f"{CREATION}/projects/{args.project_id}")
        if not report.check(
            "GET /projects/{id} returns 200 (project exists and is yours)",
            project.status_code == 200,
            project.text[:300],
        ):
            return 1
        project_row = project.json()
        payloads["project"] = project_row
        print(f"\n  project      : {project_row['name']} ({project_row['id']})")
        print(f"  description  : {(project_row.get('description') or '')[:120]}...")

        tree = client.get(
            f"{CREATION}/projects/{args.project_id}/tree", params={"depth": args.depth}
        )
        if not report.check("GET /projects/{id}/tree returns 200", tree.status_code == 200):
            return 1
        tree_row = tree.json()["tree"]
        payloads["tree_before"] = tree_row
        before = sorted(item["path"] for item in files(tree_row))
        print(f"  files before : {len(before)}")

        suggestion = client.post(
            SUGGEST,
            data={"project_id": args.project_id},
            files={"file": (document.name, document.read_bytes(), "text/markdown")},
        )
        if not report.check(
            "POST /suggestions returns 200",
            suggestion.status_code == 200,
            suggestion.text[:400],
        ):
            return 1

        payload = suggestion.json()
        payloads["suggestions"] = payload
        print_suggestions(payload)

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
        report.check("at least one suggestion is offered", bool(paths))
        report.check("the project root is offered", "" in paths, paths)
        report.check(
            "ranks run 1..n",
            [item["rank"] for item in payload["suggestions"]] == list(range(1, len(paths) + 1)),
        )
        report.check(
            "the scan reports what it cost, without a model call",
            payload["scan"]["folders_scored"] >= 1 and bool(payload["scan"]["scorer_version"]),
            payload["scan"],
        )
        if args.expect:
            report.check(
                f"'{args.expect}' is among the suggestions",
                args.expect in paths,
                paths,
            )

        if args.suggest_only:
            report.summary()
            return 0 if not report.failures else 1

        target = payload["suggestions"][0]
        directory_id = target["directory_id"]
        directory_path = target["path"]
        if args.directory:
            chosen = find_directory(client, args.project_id, args.directory, depth=args.depth)
            if not report.check(
                f"the directory '{args.directory}' exists in the project",
                chosen is not None,
            ):
                return 1
            directory_id = chosen["id"]
            directory_path = chosen["path"]

        print(f"\n  -> placing into: {directory_path or '(project root)'} ({directory_id})")
        print(f"     placement    : {args.placement}")

        placement: dict[str, Any] = {
            "request_id": payload["request_id"],
            "directory_id": directory_id,
            "placement": args.placement,
        }
        if args.placement == "new_directory":
            placement["new_directory_name"] = args.new_directory_name
        if args.file_name:
            placement["file_name"] = args.file_name

        placed = client.post(PLACE, json=placement)
        if placed.status_code == 409:
            print("\n  conflict:")
            print(json.dumps(placed.json().get("detail"), indent=2))
            report.check("POST /placements succeeds", False, "the name is taken")
            report.summary()
            return 2
        if not report.check(
            "POST /placements returns 201", placed.status_code == 201, placed.text[:400]
        ):
            return 1

        result = placed.json()
        payloads["placement"] = result
        expected_dir = directory_path
        if args.placement == "new_directory" and args.new_directory_name:
            expected_dir = (
                f"{directory_path}/{args.new_directory_name}"
                if directory_path
                else args.new_directory_name
            )
        expected_path = f"{expected_dir}/{document.name}" if expected_dir else document.name

        print(f"\n  placed       : {result['file']['path']}")
        print(f"  descriptions : {result['refreshed_directories']} refreshed")
        print(f"  file id      : {result['file']['id']}")
        print(f"  storage      : {result['file']['storage_path']}")

        report.check(
            "the file landed where the request said",
            result["file"]["path"] == expected_path,
            f"{result['file']['path']} != {expected_path}",
        )
        report.check(
            "the folder and its ancestors were re-described",
            result["refreshed_directories"] >= 1,
            result["refreshed_directories"],
        )
        report.check(
            "the blob is content-addressed in the project",
            result["file"]["storage_path"].startswith(f"{args.project_id}/")
            and result["file"]["storage_path"].endswith(".md"),
            result["file"]["storage_path"],
        )

        after_tree = client.get(
            f"{CREATION}/projects/{args.project_id}/tree", params={"depth": args.depth}
        )
        if not report.check(
            "GET /projects/{id}/tree returns 200 after placing", after_tree.status_code == 200
        ):
            return 1

        tree_after = after_tree.json()["tree"]
        payloads["tree_after"] = tree_after
        after = sorted(item["path"] for item in files(tree_after))
        report.check(
            "the new file is in the tree",
            result["file"]["path"] in after,
            f"{len(before)} -> {len(after)} files",
        )
        report.check(
            "only the new file was added",
            sorted(set(after) - set(before)) == [result["file"]["path"]],
            sorted(set(after) - set(before)),
        )

        refreshed = next(
            (row for row in directories(tree_after) if row["id"] == result["directory_id"]),
            None,
        )
        if refreshed is not None:
            print(f"\n  {refreshed['path'] or '(project root)'} now says:")
            print(f"    {refreshed.get('description')}")

    report.summary()
    if args.json:
        print(json.dumps(payloads, indent=2, default=str))
    return 0 if not report.failures else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--project-id", required=True, help="project to add the document to")
    parser.add_argument("--document", required=True, type=Path, help="markdown file to add")
    parser.add_argument(
        "--user",
        default=None,
        help="X-Dev-User-Id to send when AUTH_MODE=dev (default: DEV_USER_ID from .env)",
    )
    parser.add_argument("--token", help="Supabase access token; omit to use the dev header")
    parser.add_argument(
        "--suggest-only",
        action="store_true",
        help="ask for suggestions and stop: nothing is written",
    )
    parser.add_argument(
        "--directory",
        help="target directory id or project-relative path (default: the top suggestion)",
    )
    parser.add_argument(
        "--placement",
        choices=("direct", "new_directory"),
        default="direct",
        help="add the file to the directory, or create a folder there first",
    )
    parser.add_argument("--new-directory-name", help="folder name for --placement new_directory")
    parser.add_argument("--file-name", help="store the document under another name")
    parser.add_argument("--expect", help="assert this path is among the suggestions")
    parser.add_argument("--depth", type=int, default=6, help="tree depth to read and print")
    parser.add_argument(
        "--timeout",
        type=float,
        default=300.0,
        help="seconds to wait for a response (model calls are slow)",
    )
    parser.add_argument("--json", action="store_true", help="also dump the payloads as JSON")
    return parser


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    args = build_parser().parse_args(argv)
    if args.user is None:
        args.user = get_settings().dev_user_id

    settings = get_settings()
    if not settings.supabase_configured:
        print("Supabase is not configured: fill SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY.")
        return 1
    if args.placement == "new_directory" and not args.new_directory_name:
        print("--new-directory-name is required with --placement new_directory")
        return 1

    document = args.document
    if not document.is_file():
        print(f"not a file: {document}")
        return 1
    if document.suffix.lower() not in MARKDOWN_SUFFIXES:
        print(f"{document.name}: only markdown documents can be added")
        return 1
    if not document.read_bytes():
        print(f"{document.name} is empty")
        return 1

    report = Report()
    payloads: dict[str, Any] = {}
    try:
        code = run(args, document, report, payloads)
    except httpx2.HTTPError as exc:
        print(f"\ntransport error: {exc}")
        return 1
    return code


if __name__ == "__main__":
    sys.exit(main())
