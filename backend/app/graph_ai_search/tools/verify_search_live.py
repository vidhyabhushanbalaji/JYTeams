#!/usr/bin/env python3
# ruff: noqa: E402 - the executable path bootstrap below must run before the ``app`` imports.
"""Live check: search a real project, through the real route (read-only).

Run from ``backend/`` (needs a configured ``.env``):

    ../.venv/bin/python -m app.graph_ai_search.tools.verify_search_live \
        --project-id <uuid> --user <owner-uuid>

    # only one query, or a different limit
    ... --only rollback --limit 3

Search never writes — no rows, no blobs, no re-description — so this is safe to run any time.
Each query is asserted: the document the query is about must come back in the top two, and a
query the project cannot answer must not return a confident hit. The optional
``max_directories`` valve is exercised once at the end.

Exit codes: 0 every check passed, 1 a check failed.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import httpx2

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.main import create_app

Row = dict[str, Any]

SEARCH = "/api/graph-ai-search/projects/{project_id}/search"

#: (query, the document that must be in the top two). Matching is local, so a case only passes
#: if the project's own descriptions and documents use this vocabulary.
CASES = [
    ("how do I roll back a bad production release", "guides/rollback-deployment.md"),
    (
        "authentication requirements and endpoint schemas for the telemetry API",
        "docs/api-reference.md",
    ),
    ("how does event ingestion scale with Redis and TimescaleDB", "docs/architecture.md"),
    ("pull request and commit standards for contributing", "CONTRIBUTING.md"),
    ("kubernetes helm deployment steps for production", "guides/deployment.md"),
]
NEGATIVE = "quarterly pricing tiers and invoicing"

HIT_KEYS = {
    "file_id",
    "name",
    "path",
    "directory_id",
    "directory_path",
    "score",
    "matched_terms",
    "excerpt",
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


def build_client(args: argparse.Namespace) -> TestClient:
    """The real app; a cold search reads documents, so the timeout is generous."""
    client = TestClient(create_app())
    client.timeout = httpx2.Timeout(args.timeout)
    if args.token:
        client.headers["Authorization"] = f"Bearer {args.token}"
    else:
        client.headers["X-Dev-User-Id"] = args.user
    return client


def search(client: TestClient, args: argparse.Namespace, query: str, **extra: Any):
    params: dict[str, Any] = {"q": query, "limit": args.limit, **extra}
    return client.get(SEARCH.format(project_id=args.project_id), params=params)


def print_payload(payload: Row) -> None:
    hits = payload["results"]
    if not hits:
        print("      (no documents matched)")
    for rank, hit in enumerate(hits, start=1):
        terms = ", ".join(hit["matched_terms"]) or "name only"
        print(f"      {rank}. {hit['score']:.2f}  {hit['path']}  [{terms}]")
        print(f"         {hit['excerpt'][:110]}")
    opened = [path or "(project root)" for path in payload["opened_directories"]]
    traversal = payload["traversal"]
    print(
        f"      opened: {', '.join(opened) or 'none'}  "
        f"(visited {traversal['directories_visited']}, "
        f"read {traversal['files_read']}, "
        f"fallback {traversal['fallback_used']}, "
        f"degraded {traversal['degraded']}, "
        f"scorer {traversal['scorer_version']})"
    )


def run(args: argparse.Namespace, report: Report, payloads: dict[str, Any]) -> int:
    settings = get_settings()
    print(f"Graph AI Search — live check against project {args.project_id}")
    print(f"  api        : in-process ({settings.supabase_url or 'SUPABASE_URL missing'})")
    print(
        f"  scorer     : local (no model calls), "
        f"folder threshold {settings.scoring_folder_threshold}"
    )
    print(f"  identity   : {'bearer token' if args.token else 'X-Dev-User-Id ' + args.user}")
    print(f"  limit      : {args.limit}")

    cases = [
        case
        for case in CASES
        if not args.only
        or args.only.lower() in case[0].lower()
        or args.only.lower() in case[1].lower()
    ]
    if not cases:
        print(f"no query or expected path matches --only {args.only!r}")
        return 1

    with build_client(args) as client:
        for query, expected in cases:
            print(f"\n? {query}")
            response = search(client, args, query)
            if not report.check(
                "GET /search returns 200", response.status_code == 200, response.text[:400]
            ):
                continue

            payload = response.json()
            payloads[query] = payload
            print_payload(payload)

            report.check(
                "the response carries the documented fields",
                set(payload)
                == {
                    "query",
                    "context",
                    "project_id",
                    "results",
                    "directories",
                    "opened_directories",
                    "traversal",
                }
                and all(set(hit) == HIT_KEYS for hit in payload["results"]),
            )
            report.check("the query is echoed back", payload["query"] == query)
            report.check(
                "the walk was not degraded",
                payload["traversal"]["degraded"] is False,
                payload["traversal"],
            )
            paths = [hit["path"] for hit in payload["results"]]
            report.check(
                f"'{expected}' is in the top two",
                expected in paths[:2],
                paths or "(nothing matched)",
            )

        print(f"\n? {NEGATIVE}  (expected: no confident hit)")
        negative = search(client, args, NEGATIVE)
        if report.check(
            "the negative query returns 200", negative.status_code == 200, negative.text[:400]
        ):
            payload = negative.json()
            payloads[NEGATIVE] = payload
            print_payload(payload)
            scores = [hit["score"] for hit in payload["results"]]
            report.check(
                "no confident hit for a query the project cannot answer",
                not scores or max(scores) < 0.6,
                scores,
            )

        if cases:
            query = cases[0][0]
            print(f"\n? {query}  (with max_directories=1)")
            valve = search(client, args, query, max_directories=1)
            if report.check("the valve is accepted", valve.status_code == 200, valve.text[:400]):
                payload = valve.json()
                payloads["valve"] = payload
                print_payload(payload)
                report.check(
                    "the valve stops after one folder",
                    payload["traversal"]["budget_exhausted"] is True
                    and len(payload["opened_directories"]) == 1,
                    payload["traversal"]["budget_exhausted"],
                )

    report.summary()
    if args.json:
        print(json.dumps(payloads, indent=2, default=str))
    return 0 if not report.failures else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--project-id", required=True, help="project to search")
    parser.add_argument(
        "--user",
        default=None,
        help="X-Dev-User-Id to send when AUTH_MODE=dev (default: DEV_USER_ID from .env)",
    )
    parser.add_argument("--token", help="Supabase access token; omit to use the dev header")
    parser.add_argument("--limit", type=int, default=5, help="results per query")
    parser.add_argument("--only", help="run only queries containing this text")
    parser.add_argument(
        "--timeout",
        type=float,
        default=300.0,
        help="seconds to wait for a response (a cold cache reads documents)",
    )
    parser.add_argument("--json", action="store_true", help="also dump the payloads")
    return parser


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    args = build_parser().parse_args(argv)
    if args.user is None:
        args.user = get_settings().dev_user_id
    if not get_settings().supabase_configured:
        print("Supabase is not configured: fill SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY.")
        return 1

    try:
        return run(args, Report(), {})
    except httpx2.HTTPError as exc:
        print(f"\ntransport error: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
