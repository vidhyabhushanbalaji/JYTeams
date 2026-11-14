#!/usr/bin/env python3
# ruff: noqa: E402 - the executable path bootstrap below must run before the ``app`` imports.
"""Executable search check on the PulseAPI example tree (offline, no quota).

Run from ``backend/``:

    ../.venv/bin/python -m app.graph_ai_search.tools.verify_search
    ../.venv/bin/python -m app.graph_ai_search.tools.verify_search --json
    ./app/graph_ai_search/tools/verify_search.py     # after chmod +x, with the venv active

The tree is the one already in the database — ``README.md``, ``CONTRIBUTING.md``,
``docs/{api-reference,architecture}.md`` and ``guides/{deployment,rollback-deployment}.md`` —
seeded with the real stored summaries, so the walk sees exactly what the production index
holds. The offline searcher replaces Gemini, so this runs with no key and no network.

Each query is asserted: the document the query is about must come back in the top two, and
a query about something the project does not cover must return nothing.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from app.core.config import get_settings
from app.graph_ai_search.llm import MockSearcher
from app.graph_ai_search.service import GraphSearchService
from app.graph_ai_search.tests.fakes import InMemorySearchRepository

Row = dict[str, Any]

#: The real summaries, exactly as stored by Graph Creation for the PulseAPI project.
TREE = {
    "name": "Docs",
    "description": (
        "This folder serves as the project root for PulseAPI, containing core introductory "
        "and contribution documentation alongside dedicated directories for deeper technical "
        "insights."
    ),
    "directories": [
        {
            "name": "docs",
            "description": (
                "Reference material for integrating with PulseAPI: the HTTP API reference and "
                "the system architecture behind event ingestion."
            ),
            "files": [
                (
                    "api-reference.md",
                    "This document provides the base URL, authentication requirements, and "
                    "endpoint details for the Pulse telemetry API, including request and "
                    "response schemas for event ingestion.",
                ),
                (
                    "architecture.md",
                    "PulseAPI decouples event ingestion from data persistence using an API "
                    "gateway, Redis Streams, and TimescaleDB to handle traffic spikes. It "
                    "outlines the end-to-end data flow and core technology stack responsible "
                    "for request routing, temporary buffering, and long-term storage.",
                ),
            ],
        },
        {
            "name": "guides",
            "description": (
                "Step-by-step operational procedures for running PulseAPI in production: "
                "deploying with Helm and rolling back a failed release."
            ),
            "files": [
                (
                    "deployment.md",
                    "This guide outlines the prerequisites and step-by-step instructions for "
                    "deploying PulseAPI to a production Kubernetes cluster using Helm. It "
                    "covers secret management, namespace creation, and health verification.",
                ),
                (
                    "rollback-deployment.md",
                    "This document provides a step-by-step guide for performing a Helm rollback "
                    "in production when a release fails, including how to verify revisions, "
                    "monitor pod status, and confirm health checks.",
                ),
            ],
        },
    ],
    "files": [
        (
            "README.md",
            "PulseAPI is a lightweight, high-throughput telemetry and event ingestion service "
            "featuring sub-5ms processing, automatic schema validation, and multi-tenant "
            "isolation. This document provides an overview of its core features, quick start "
            "instructions, and links to architectural and deployment documentation.",
        ),
        (
            "CONTRIBUTING.md",
            "This file outlines the guidelines for contributing to the PulseAPI project, "
            "detailing the development workflow, testing requirements, and commit standards "
            "for pull requests.",
        ),
    ],
}

#: (query, the document that must be in the top two). The offline searcher matches keywords,
#: so each query shares vocabulary with the stored descriptions — the live check uses natural
#: phrasing instead, where Gemini does the judging.
CASES = [
    ("how do I roll back a bad production release", "guides/rollback-deployment.md"),
    ("API reference authentication requirements and endpoint schemas", "docs/api-reference.md"),
    ("event ingestion Redis Streams TimescaleDB", "docs/architecture.md"),
    ("pull request and commit standards", "CONTRIBUTING.md"),
    ("kubernetes helm production cluster deployment", "guides/deployment.md"),
]
#: A query this project cannot answer: nothing should be logged.
NEGATIVE = "quarterly pricing tiers and invoicing"


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


def seed(repository: InMemorySearchRepository, owner_id: str) -> dict[str, Any]:
    """Load the PulseAPI tree exactly as the project stores it."""
    project = repository.seed_project(owner_id=owner_id, name=TREE["name"])
    repository.directories[project["root_directory_id"]]["description"] = TREE["description"]

    for name, summary in TREE["files"]:
        repository.seed_file(
            project["id"],
            directory_id=project["root_directory_id"],
            name=name,
            summary=summary,
        )

    for folder in TREE["directories"]:
        row = repository.seed_directory(
            project["id"],
            parent_id=project["root_directory_id"],
            name=folder["name"],
            description=folder["description"],
        )
        for name, summary in folder["files"]:
            repository.seed_file(project["id"], directory_id=row["id"], name=name, summary=summary)

    return project


def print_hits(payload: dict[str, Any]) -> None:
    """Print one query's ranked hits."""
    hits = payload["results"]
    if not hits:
        print("      (no documents matched)")
    for rank, hit in enumerate(hits, start=1):
        print(f"      {rank}. {hit['score']:.2f}  {hit['path']}")
        print(f"         {hit['reason']}")
    opened = [path or "(project root)" for path in payload["opened_directories"]]
    traversal = payload["traversal"]
    print(
        f"      opened: {', '.join(opened) or 'none'}  "
        f"(visited {traversal['directories_visited']}, "
        f"fallback {traversal['fallback_used']}, "
        f"degraded {traversal['degraded']})"
    )


async def run(args: argparse.Namespace, report: Report, payloads: dict[str, Any]) -> int:
    settings = get_settings()
    repository = InMemorySearchRepository()
    project = seed(repository, settings.dev_user_id)
    service = GraphSearchService(repository=repository, searcher=MockSearcher(), settings=settings)

    print("Graph AI Search — example-tree check (offline, mock searcher)")
    print(f"  project : {project['name']} ({len(repository.files)} documents)")
    print(
        "  tree    : README, CONTRIBUTING, docs/{api-reference,architecture}, "
        "guides/{deployment,rollback-deployment}"
    )

    for query, expected in CASES:
        print(f"\n? {query}")
        payload = await service.search(
            project_id=project["id"], owner_id=settings.dev_user_id, query=query, limit=5
        )
        payloads[query] = payload
        print_hits(payload)
        paths = [hit["path"] for hit in payload["results"]]
        report.check(
            f"'{expected}' is in the top two",
            expected in paths[:2],
            paths or "(nothing matched)",
        )
        report.check(
            "the response carries the documented fields",
            set(payload) == {"query", "project_id", "results", "opened_directories", "traversal"}
            and all(
                set(hit)
                == {
                    "file_id",
                    "name",
                    "path",
                    "directory_id",
                    "directory_path",
                    "summary",
                    "score",
                    "reason",
                }
                for hit in payload["results"]
            ),
        )

    print(f"\n? {NEGATIVE}  (expected: nothing)")
    negative = await service.search(
        project_id=project["id"], owner_id=settings.dev_user_id, query=NEGATIVE, limit=5
    )
    payloads[NEGATIVE] = negative
    print_hits(negative)
    report.check(
        "a query the project cannot answer returns nothing",
        negative["results"] == [],
        [hit["path"] for hit in negative["results"]],
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
    parser.add_argument("--json", action="store_true", help="also print the payloads")
    return parser


def main(argv: list[str] | None = None) -> int:
    import asyncio

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    args = build_parser().parse_args(argv)
    return asyncio.run(run(args, Report(), {}))


if __name__ == "__main__":
    sys.exit(main())
