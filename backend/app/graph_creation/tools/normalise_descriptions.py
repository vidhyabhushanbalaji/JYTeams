"""Rewrite existing folder descriptions as plain prose (no model call).

New descriptions are naturalised as they are written (``clip_description``), but rows created
before that rule may still say ``rollback-plan`` or ``deploy_run``. This tool rewrites those rows
in place: separators become spaces, every word is kept, no model is called, and nothing else about
the tree changes.

Run from ``backend/``::

    ..\\.venv\\Scripts\\python.exe -m app.graph_creation.tools.normalise_descriptions
    ..\\.venv\\Scripts\\python.exe -m app.graph_creation.tools.normalise_descriptions --apply

Without ``--apply`` nothing is written (it only reports). Add ``--project-id`` to limit the sweep
to one project.
"""

from __future__ import annotations

import argparse

from app.core.text import naturalise_description
from app.db.supabase import admin_client


def _rows(table: str, project_id: str | None) -> list[dict]:
    def run() -> list[dict]:
        builder = admin_client().table(table).select("id, description")
        if project_id:
            builder = (
                builder.eq("id", project_id)
                if table == "projects"
                else builder.eq("project_id", project_id)
            )
        response = builder.not_.is_("description", "null").execute()
        return response.data or []

    return run()


def _rewrite(table: str, updates: list[tuple[str, str]], apply: bool) -> int:
    written = 0
    for row_id, description in updates:
        if apply:
            admin_client().table(table).update({"description": description}).eq(
                "id", row_id
            ).execute()
        written += 1
    return written


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-id", help="Only this project's tree and description")
    parser.add_argument("--apply", action="store_true", help="Write the changes (default: report)")
    args = parser.parse_args()

    total = 0
    for table in ("directories", "projects"):
        rows = _rows(table, args.project_id)
        updates = [
            (str(row["id"]), naturalise_description(str(row["description"])))
            for row in rows
            if naturalise_description(str(row["description"])) != str(row["description"])
        ]
        for row in rows[:3]:
            before = str(row["description"])
            after = naturalise_description(before)
            if before != after:
                print(f"  {table} {row['id']}: {before!r} -> {after!r}")
        if len(updates) > 3:
            print(f"  {table}: {len(updates)} description(s) to rewrite")
        total += _rewrite(table, updates, args.apply)

    verb = "rewrote" if args.apply else "would rewrite"
    print(f"{verb} {total} description(s)." + ("" if args.apply else " Re-run with --apply."))


if __name__ == "__main__":
    main()
