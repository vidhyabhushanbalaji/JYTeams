r"""Upload a local directory to a running JYTeams API and print the resulting tree.

Run from ``backend/``:

    python -m app.graph_creation.tools.upload_directory ..\..\docs
    python -m app.graph_creation.tools.upload_directory ..\..\docs --dry-run
    python -m app.graph_creation.tools.upload_directory ..\..\docs --mode add --project-id <uuid>

The live run uploads the directory, polls the creation job and then prints the tree exactly
as the API returns it (directory descriptions and per-file summaries). ``--dry-run`` never
touches the network: it validates the directory and previews the same bottom-up summaries
with the offline mock summariser, which is useful before Supabase is configured.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import textwrap
import time
from pathlib import Path

import httpx

from app.core.config import get_settings
from app.graph_creation.extract import extract_text
from app.graph_creation.summarise import MockSummarizer
from app.graph_creation.tree import (
    DirectoryNode,
    FileEntry,
    UploadValidationError,
    build_tree,
    postorder,
)

API_PREFIX = "/api/graph-creation"
FINISHED = {"ok", "partial", "failed"}
SKIP_DIRECTORIES = {
    ".git",
    ".idea",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    ".vscode",
    "__pycache__",
    "node_modules",
}
WRAP_WIDTH = 100


def human_size(size: int) -> str:
    """Format a byte count for the tree output."""
    value = float(size)
    for unit in ("B", "KB", "MB", "GB"):
        if value < 1024 or unit == "GB":
            return f"{value:.0f} {unit}" if unit == "B" else f"{value:.1f} {unit}"
        value /= 1024
    return f"{size} B"


def collect_local_files(directory: Path) -> list[tuple[str, bytes]]:
    """Read ``directory`` into ``(relative posix path, bytes)`` pairs."""
    if not directory.is_dir():
        raise SystemExit(f"not a directory: {directory}")

    collected: list[tuple[str, bytes]] = []
    for path in sorted(directory.rglob("*")):
        if not path.is_file():
            continue
        parts = path.relative_to(directory).parts
        if any(part in SKIP_DIRECTORIES for part in parts):
            continue
        collected.append(("/".join(parts), path.read_bytes()))

    if not collected:
        raise SystemExit(f"no files found in {directory}")
    return collected


def emit(text: str | None, indent: str, *, full: bool) -> None:
    """Print a summary or description, wrapped unless ``--full`` was passed."""
    if not text:
        return
    if full:
        print(indent + text)
        return
    print(
        textwrap.fill(
            text,
            width=WRAP_WIDTH,
            initial_indent=indent,
            subsequent_indent=indent,
        )
    )


async def preview_local(entries: list[tuple[str, bytes]], *, full: bool) -> int:
    """Validate the directory locally and preview the tree with the mock summariser."""
    settings = get_settings()
    try:
        tree = build_tree(
            [FileEntry(path, data) for path, data in entries],
            max_depth=settings.max_directory_depth,
            max_files=settings.max_upload_files,
        )
    except UploadValidationError as exc:
        print(f"invalid directory: {exc}")
        return 1

    summariser = MockSummarizer()
    summaries: dict[str, str] = {}
    descriptions: dict[str, str] = {}

    for node in postorder(tree):
        for entry in node.files:
            extracted = extract_text(
                entry.data,
                filename=entry.name,
                max_chars=settings.summary_max_input_chars,
            )
            summaries[entry.path] = (
                await summariser.summarise_file(name=entry.name, text=extracted.text or "")
                if extracted.ok
                else f"[skipped: {extracted.reason}]"
            )
        descriptions[node.path] = await summariser.summarise_directory(
            path=node.path,
            files=[(entry.name, summaries[entry.path]) for entry in node.files],
            directories=[(child.name, descriptions[child.path]) for child in node.directories],
        )

    directories = list(postorder(tree))
    print(f"DRY RUN - {tree.total_files} file(s), {len(directories)} directory node(s), no network")
    print()
    _print_local(tree, summaries, descriptions, full=full)
    print()
    print("bottom-up summary order (this is how descriptions are produced):")
    for node in directories:
        print(f"  {node.path or '(project root)'}")
    return 0


def _print_local(
    node: DirectoryNode,
    summaries: dict[str, str],
    descriptions: dict[str, str],
    *,
    full: bool,
    prefix: str = "",
) -> None:
    print(
        f"{prefix}[D] {node.path or '(project root)'}  depth={node.depth} "
        f"files={node.direct_file_count} dirs={node.child_directory_count} "
        f"ltree={node.ltree_path or '-'}"
    )
    emit(descriptions.get(node.path), prefix + "    ", full=full)
    for entry in node.files:
        print(f"{prefix}    [F] {entry.path}  {human_size(entry.size)}")
        emit(summaries.get(entry.path), prefix + "        ", full=full)
    for child in node.directories:
        _print_local(child, summaries, descriptions, full=full, prefix=prefix + "    ")


async def upload_and_print(args: argparse.Namespace, entries: list[tuple[str, bytes]]) -> int:
    """Upload the directory, follow the job, then print the stored tree."""
    base = args.url.rstrip("/")
    headers = (
        {"Authorization": f"Bearer {args.token}"}
        if args.token
        else {"X-Dev-User-Id": args.user or get_settings().dev_user_id}
    )
    form: dict[str, str] = {"mode": args.mode}
    if args.name:
        form["name"] = args.name
    if args.project_id:
        form["project_id"] = args.project_id
    files = [("files", (path, data, "text/markdown")) for path, data in entries]

    timeout = httpx.Timeout(120.0, connect=10.0)
    async with httpx.AsyncClient(timeout=timeout, headers=headers) as client:
        print(f"POST {base}{API_PREFIX}/uploads  ({len(entries)} file(s), mode={args.mode})")
        response = await client.post(f"{base}{API_PREFIX}/uploads", data=form, files=files)
        if response.status_code >= 400:
            print(f"upload rejected: HTTP {response.status_code}\n{_detail(response)}")
            return 1

        accepted = response.json()
        print(
            f"  accepted: project={accepted['project_id']} "
            f"job={accepted['job_id']} files={accepted['total_files']}"
        )

        job = await _poll_job(client, base, accepted["job_id"], args)
        if job is None:
            return 1
        print(
            f"  job {job['status']}: {job['processed_files']}/{job['total_files']} files, "
            f"{job['failed_files']} failed"
        )
        if job["status"] == "failed":
            print(f"  error: {job.get('error')}")
            return 1

        params = {"depth": args.depth} if args.depth is not None else None
        response = await client.get(
            f"{base}{API_PREFIX}/projects/{accepted['project_id']}/tree",
            params=params,
        )
        if response.status_code >= 400:
            print(f"tree fetch failed: HTTP {response.status_code}\n{_detail(response)}")
            return 1
        payload = response.json()

    if args.json:
        print(json.dumps(payload, indent=2))
        return 0

    project = payload["project"]
    print(f"\nproject: {project['name']}  ({project['id']})")
    emit(project.get("description") or "(no description)", "  ", full=args.full)
    print()
    _print_api(payload["tree"], full=args.full)
    return 0


async def _poll_job(
    client: httpx.AsyncClient,
    base: str,
    job_id: str,
    args: argparse.Namespace,
) -> dict | None:
    deadline = time.monotonic() + args.timeout
    last: str | None = None
    while True:
        response = await client.get(f"{base}{API_PREFIX}/jobs/{job_id}")
        if response.status_code >= 400:
            print(f"job poll failed: HTTP {response.status_code}\n{_detail(response)}")
            return None

        job = response.json()
        if job["status"] != last:
            last = job["status"]
            print(f"  job {last}  {job['processed_files']}/{job['total_files']}")
        if job["status"] in FINISHED:
            return job
        if time.monotonic() > deadline:
            print(f"timed out after {args.timeout:.0f}s (still {job['status']})")
            return job
        await asyncio.sleep(args.interval)


def _detail(response: httpx.Response) -> str:
    """Render the API error detail without a traceback."""
    try:
        body = response.json()
    except json.JSONDecodeError:
        return response.text[:500]
    detail = body.get("detail", body) if isinstance(body, dict) else body
    return detail if isinstance(detail, str) else json.dumps(detail, indent=2)


def _print_api(row: dict, *, full: bool, prefix: str = "") -> None:
    print(
        f"{prefix}[D] {row['path'] or '(project root)'}  depth={row['depth']} "
        f"files={row['direct_file_count']} dirs={row['child_directory_count']}"
    )
    emit(row.get("description"), prefix + "    ", full=full)
    for item in row.get("files", []):
        size = human_size(item["size_bytes"])
        print(f"{prefix}    [F] {item['path']}  {size}  {item['summary_status']}")
        emit(item.get("summary"), prefix + "        ", full=full)
    for child in row.get("directories", []):
        _print_api(child, full=full, prefix=prefix + "    ")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("directory", type=Path, help="local directory to upload")
    parser.add_argument(
        "--url",
        default="http://127.0.0.1:8000",
        help="API base URL (default: %(default)s)",
    )
    parser.add_argument(
        "--mode",
        choices=("new", "add"),
        default="new",
        help="new = build a project tree, add = extend an existing one",
    )
    parser.add_argument("--name", help="project name (mode=new)")
    parser.add_argument("--project-id", help="project to extend (mode=add)")
    parser.add_argument("--token", help="Supabase access token; omit to use the dev header")
    parser.add_argument(
        "--user",
        default=None,
        help="X-Dev-User-Id value (default: DEV_USER_ID from backend/.env)",
    )
    parser.add_argument("--depth", type=int, help="limit the printed tree depth")
    parser.add_argument("--timeout", type=float, default=300.0, help="seconds to wait for the job")
    parser.add_argument("--interval", type=float, default=1.0, help="seconds between job polls")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="validate and preview locally, without touching the network",
    )
    parser.add_argument("--json", action="store_true", help="print the raw tree JSON")
    parser.add_argument("--full", action="store_true", help="do not shorten long summaries")
    return parser


async def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    args = build_parser().parse_args(argv)
    entries = collect_local_files(args.directory)
    if args.dry_run:
        return await preview_local(entries, full=args.full)
    return await upload_and_print(args, entries)


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
