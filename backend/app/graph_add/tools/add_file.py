r"""Add one markdown document to an existing project tree, through the real HTTP routes.

Run from ``backend/``:

    python -m app.graph_add.tools.add_file ..\..\notes\auth.md --dry-run
    python -m app.graph_add.tools.add_file ..\..\notes\auth.md --project-id <uuid>
    python -m app.graph_add.tools.add_file ..\..\notes\auth.md --project-id <uuid> \
        --choose 1 --placement direct
    python -m app.graph_add.tools.add_file ..\..\notes\auth.md --project-id <uuid> \
        --choose 2 --placement new_directory --new-directory-name authentication
    python -m app.graph_add.tools.add_file ..\..\notes\auth.md --project-id <uuid> \
        --choose 1 --auto-rename

The script walks the same path as the frontend wizard: it uploads the document for
suggestions, prints the ranked places it could go with the reason for each, asks which one
to use (and whether to create a folder at that point), then commits the choice. With no
selection flags it prompts; with them it runs unattended. ``--dry-run`` never touches the
network.

Exit codes: 0 placed, 1 error, 2 name conflict (see the printed alternatives), 3 the
suggestion expired, 130 nothing was written because the user quit.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import textwrap
from pathlib import Path

import httpx

from app.core.config import get_settings
from app.graph_add.extract import MARKDOWN_SUFFIXES, extract_text

API_PREFIX = "/api/graph-add"
CREATION_PREFIX = "/api/graph-creation"
DEFAULT_USER = "00000000-0000-0000-0000-000000000001"
WRAP_WIDTH = 100

EXIT_OK = 0
EXIT_ERROR = 1
EXIT_CONFLICT = 2
EXIT_EXPIRED = 3
EXIT_ABORTED = 130


def human_size(size: int) -> str:
    """Format a byte count for the printed output."""
    value = float(size)
    for unit in ("B", "KB", "MB", "GB"):
        if value < 1024 or unit == "GB":
            return f"{value:.0f} {unit}" if unit == "B" else f"{value:.1f} {unit}"
        value /= 1024
    return f"{size} B"


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


def _detail(response: httpx.Response) -> str:
    """Render the API error detail without a traceback."""
    try:
        body = response.json()
    except json.JSONDecodeError:
        return response.text[:500]
    detail = body.get("detail", body) if isinstance(body, dict) else body
    return detail if isinstance(detail, str) else json.dumps(detail, indent=2)


def _fail(response: httpx.Response) -> int:
    """Explain a failed call and map the status onto an exit code."""
    print(f"HTTP {response.status_code}")
    print(textwrap.indent(_detail(response), "  "))
    if response.status_code in {410, 409}:
        alternatives = _alternatives(response)
        if alternatives:
            print(f"  retry with --file-name {alternatives[0]!r}, or pass --auto-rename")
    if response.status_code == 410:
        print("  the suggestion expired; run the script again")
        return EXIT_EXPIRED
    if response.status_code == 409:
        return EXIT_CONFLICT
    return EXIT_ERROR


def _headers(args: argparse.Namespace) -> dict[str, str]:
    """Bearer token when one was given, otherwise the dev header."""
    if args.token:
        return {"Authorization": f"Bearer {args.token}"}
    return {"X-Dev-User-Id": args.user}


def _interactive(args: argparse.Namespace) -> bool:
    """Prompt only when the caller chose nothing *and* stdin is a terminal.

    Any selection flag makes the run unattended, so a scripted call never blocks on input —
    a name clash then surfaces as exit code 2 with the alternatives printed.
    """
    return (
        sys.stdin.isatty()
        and args.choose is None
        and not args.directory_id
        and not args.root
        and args.placement is None
        and not args.file_name
        and not args.auto_rename
    )


def print_suggestions(payload: dict, *, full: bool) -> None:
    """Show the ranked places the document could go."""
    brief = payload["file"]
    print(
        f"{brief['name']}  ({human_size(brief['size_bytes'])}, "
        f"sha256 {brief['content_sha256'][:12]}...)"
    )
    emit(f"preview: {brief['preview']}", "  ", full=full)
    print()
    print(f"  {'#':>2}  {'score':>5}  {'path':<32}  {'files/dirs':>10}  leaf  reason")

    for item in payload["suggestions"]:
        path = item["path"] or "(project root)"
        counts = f"{item['direct_file_count']}/{item['child_directory_count']}"
        leaf = "yes" if item["is_leaf"] else "no"
        print(
            f"  {item['rank']:>2}  {item['score']:>5.2f}  {path:<32}  {counts:>10}  "
            f"{leaf:<4}  {item['reason']}"
        )
        if item["proposed_new_directory_names"]:
            names = ", ".join(item["proposed_new_directory_names"])
            print(f"        new folder names: {names}")
        if not item["name_available"]:
            taken = ", ".join(item["suggested_file_names"]) or "(no alternative found)"
            print(f"        '{brief['name']}' is taken here; alternatives: {taken}")
        if item["identical_content_at"]:
            twins = ", ".join(item["identical_content_at"])
            print(f"        identical content already at: {twins}")

    scan = payload["scan"]
    print()
    print(
        f"  scan: folders_scored={scan['folders_scored']} threshold={scan['threshold']} "
        f"scorer={scan['scorer_version']} (no model call)"
    )


def print_placement(placed: dict) -> None:
    """Show where the document landed."""
    file = placed["file"]
    where = placed["directory_path"] or "(project root)"
    kind = "folder created" if placed["created_directory"] else "existing folder"
    print()
    print(f"Placed: {file['path']}")
    print(f"  directory: {where}  ({kind})")
    print(f"  descriptions refreshed: {placed['refreshed_directories']}")
    print(f"  file id: {file['id']}  size {human_size(file['size_bytes'])}")
    if file.get("storage_path"):
        print(f"  storage: {file.get('storage_bucket')}/{file['storage_path']}")


def print_node(row: dict, *, full: bool, prefix: str = "") -> None:
    """Render one directory of a project tree."""
    print(
        f"{prefix}[D] {row['path'] or '(project root)'}  depth={row['depth']} "
        f"files={row['direct_file_count']} dirs={row['child_directory_count']}"
    )
    emit(row.get("description"), prefix + "    ", full=full)
    for item in row.get("files", []):
        print(f"{prefix}    [F] {item['path']}  {human_size(item['size_bytes'])}")
    for child in row.get("directories", []):
        print_node(child, full=full, prefix=prefix + "    ")


def choose_directory(payload: dict, args: argparse.Namespace) -> tuple[str, str] | None:
    """Resolve which directory to use: a flag, or the prompt."""
    suggestions = payload["suggestions"]

    if args.directory_id:
        match = next(
            (item for item in suggestions if item["directory_id"] == args.directory_id),
            None,
        )
        return args.directory_id, (match["path"] if match else "")

    if args.root:
        root = next(item for item in suggestions if item["path"] == "")
        return root["directory_id"], ""

    if args.choose is not None:
        if not 1 <= args.choose <= len(suggestions):
            print(f"--choose must be between 1 and {len(suggestions)}")
            return None
        item = suggestions[args.choose - 1]
        return item["directory_id"], item["path"]

    if not _interactive(args):
        print("no directory chosen: pass --choose N, --directory-id UUID or --root")
        return None

    print()
    while True:
        answer = input(f"Choose 1-{len(suggestions)}, r for root, q to quit: ").strip().lower()
        if answer in {"q", "quit"}:
            return None
        if answer == "r":
            root = next(item for item in suggestions if item["path"] == "")
            return root["directory_id"], ""
        if answer.isdigit() and 1 <= int(answer) <= len(suggestions):
            item = suggestions[int(answer) - 1]
            return item["directory_id"], item["path"]
        print("  not a valid choice")


def choose_placement(payload: dict, args: argparse.Namespace, directory_id: str) -> dict | None:
    """Resolve direct-vs-new-folder, the folder name, and any rename."""
    item = next((s for s in payload["suggestions"] if s["directory_id"] == directory_id), None)
    interactive = _interactive(args)

    placement = args.placement
    if placement is None:
        if not interactive:
            placement = "direct"
        else:
            while True:
                answer = (
                    input("Add it here? [d]irect / [n]ew folder / [q]uit: ").strip().lower() or "d"
                )
                if answer in {"q", "quit"}:
                    return None
                if answer in {"d", "direct"}:
                    placement = "direct"
                    break
                if answer in {"n", "new", "new_directory", "new folder"}:
                    placement = "new_directory"
                    break
                print("  answer d or n")

    extra: dict = {"placement": placement}

    if placement == "new_directory":
        proposed = list((item or {}).get("proposed_new_directory_names") or [])
        name = args.new_directory_name
        if not name and interactive:
            default = proposed[0] if proposed else "new folder"
            name = input(f"New folder name [{default}]: ").strip() or default
        if not name:
            print("--new-directory-name is required with --placement new_directory")
            return None
        extra["new_directory_name"] = name

    if args.file_name:
        extra["file_name"] = args.file_name
    elif interactive and item is not None and not item["name_available"]:
        alternatives = item["suggested_file_names"]
        if alternatives:
            answer = input(
                f"'{payload['file']['name']}' is taken here; store as {alternatives[0]}? "
                "[Enter = yes, or type a name]: "
            ).strip()
            extra["file_name"] = answer or alternatives[0]

    return extra


def _alternatives(response: httpx.Response) -> list[str]:
    """The rename options a 409 conflict offered, if any."""
    try:
        detail = response.json().get("detail")
    except json.JSONDecodeError:
        return []
    if not isinstance(detail, dict):
        return []
    names = detail.get("suggested_names")
    return [str(name) for name in names] if isinstance(names, list) else []


async def _submit(
    client: httpx.AsyncClient,
    args: argparse.Namespace,
    headers: dict[str, str],
    payload: dict,
    directory_id: str,
    extra: dict,
) -> int:
    """Commit the choice, retrying once with an alternative name when asked."""
    endpoint = f"{args.url}{API_PREFIX}/placements"
    body = {"request_id": payload["request_id"], "directory_id": directory_id, **extra}
    response = await client.post(endpoint, json=body, headers=headers)

    if response.status_code == 201:
        placed = response.json()
        print(json.dumps({"placement": placed}, indent=2)) if args.json else print_placement(placed)
        return EXIT_OK

    if response.status_code == 409 and args.auto_rename and "file_name" not in body:
        alternatives = _alternatives(response)
        if alternatives:
            print(f"name taken, retrying as {alternatives[0]}")
            body["file_name"] = alternatives[0]
            retry = await client.post(endpoint, json=body, headers=headers)
            if retry.status_code == 201:
                placed = retry.json()
                print(json.dumps({"placement": placed}, indent=2)) if args.json else (
                    print_placement(placed)
                )
                return EXIT_OK
            return _fail(retry)

    return _fail(response)


async def _show_tree(
    client: httpx.AsyncClient,
    args: argparse.Namespace,
    headers: dict[str, str],
    project_id: str,
) -> None:
    """Print the project tree after placing (a read-only call to Graph Creation)."""
    params = {"depth": args.depth} if args.depth is not None else None
    response = await client.get(
        f"{args.url}{CREATION_PREFIX}/projects/{project_id}/tree",
        params=params,
        headers=headers,
    )
    print()
    if response.status_code != 200:
        print("could not read the tree:")
        print(textwrap.indent(_detail(response), "  "))
        return
    print("tree now:")
    print_node(response.json()["tree"], full=args.full, prefix="  ")


async def run(args: argparse.Namespace, name: str, data: bytes) -> int:
    """Suggest, choose, place — the whole wizard over HTTP."""
    headers = _headers(args)
    async with httpx.AsyncClient(timeout=httpx.Timeout(args.timeout)) as client:
        response = await client.post(
            f"{args.url}{API_PREFIX}/suggestions",
            data={"project_id": args.project_id},
            files={"file": (name, data, "text/markdown")},
            headers=headers,
        )
        if response.status_code != 200:
            return _fail(response)

        payload = response.json()
        if args.json:
            print(json.dumps({"suggestions": payload}, indent=2))
        else:
            print_suggestions(payload, full=args.full)

        choice = choose_directory(payload, args)
        if choice is None:
            print("nothing was written")
            return EXIT_ABORTED
        directory_id, directory_path = choice

        extra = choose_placement(payload, args, directory_id)
        if extra is None:
            print("nothing was written")
            return EXIT_ABORTED

        if not args.json:
            target = directory_path or "(project root)"
            verb = "create a folder in" if extra["placement"] == "new_directory" else "use"
            print(f"\n-> {verb} {target}")

        code = await _submit(client, args, headers, payload, directory_id, extra)
        if code == EXIT_OK and args.show_tree:
            await _show_tree(client, args, headers, payload["project_id"])
        return code


async def preview(args: argparse.Namespace, name: str, data: bytes) -> int:
    """Validate the document and show what would be sent, without any network call."""
    settings = get_settings()
    extracted = extract_text(data, filename=name, max_chars=settings.summary_max_input_chars)
    if not extracted.ok:
        print(f"{name}: {extracted.reason}")
        return EXIT_ERROR

    preview_text = " ".join((extracted.text or "").split())[:200]
    print(f"{name}  ({human_size(len(data))})")
    emit(f"preview (what the wizard shows): {preview_text}", "  ", full=args.full)
    print()
    print("suggestions are ranked locally — this dry run makes no model call")
    print()
    print("would call:")
    print(f"  POST {args.url}{API_PREFIX}/suggestions")
    print(
        f"       multipart: file={name!r} ({len(data)} bytes), "
        f"project_id={args.project_id or '<required>'}"
    )
    print(f"  POST {args.url}{API_PREFIX}/placements")
    print("       json: request_id, directory_id, placement (direct|new_directory),")
    print("             new_directory_name?, file_name?")
    print()
    print("nothing was sent")
    return EXIT_OK


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("document", type=Path, help="markdown file to add")
    parser.add_argument(
        "--url",
        default="http://127.0.0.1:8000",
        help="API base URL (default: %(default)s)",
    )
    parser.add_argument("--project-id", help="project whose tree should gain the document")

    target = parser.add_mutually_exclusive_group()
    target.add_argument(
        "--choose",
        type=int,
        metavar="N",
        help="use suggestion N (1-based); skips the prompt",
    )
    target.add_argument("--directory-id", help="use this directory; skips the prompt")
    target.add_argument("--root", action="store_true", help="use the project root")

    parser.add_argument(
        "--placement",
        choices=("direct", "new_directory"),
        help="add the file to the chosen folder, or create a folder there",
    )
    parser.add_argument(
        "--new-directory-name",
        help="folder to create (required with --placement new_directory)",
    )
    parser.add_argument("--file-name", help="store the document under another name")
    parser.add_argument(
        "--auto-rename",
        action="store_true",
        help="on a name conflict, retry once with the API's first suggestion",
    )
    parser.add_argument("--token", help="Supabase access token; omit to use the dev header")
    parser.add_argument(
        "--user",
        default=DEFAULT_USER,
        help="X-Dev-User-Id value when the API runs with AUTH_MODE=dev",
    )
    parser.add_argument("--timeout", type=float, default=60.0, help="HTTP timeout in seconds")
    parser.add_argument(
        "--show-tree",
        action="store_true",
        help="after placing, print the project tree (Graph Creation read route)",
    )
    parser.add_argument("--depth", type=int, help="tree depth to print with --show-tree")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="validate the document and show what would be sent, without the network",
    )
    parser.add_argument(
        "--json", action="store_true", help="print the raw suggestion and placement JSON"
    )
    parser.add_argument("--full", action="store_true", help="do not shorten long summaries")
    return parser


async def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    args = build_parser().parse_args(argv)

    path = args.document
    if not path.is_file():
        print(f"not a file: {path}")
        return EXIT_ERROR
    if path.suffix.lower() not in MARKDOWN_SUFFIXES:
        supported = ", ".join(sorted(MARKDOWN_SUFFIXES))
        print(f"{path.name}: only markdown documents can be added ({supported})")
        return EXIT_ERROR

    data = path.read_bytes()
    if not data:
        print(f"{path.name} is empty")
        return EXIT_ERROR

    if args.dry_run:
        return await preview(args, path.name, data)
    if not args.project_id:
        print("--project-id is required (the tree the document should join)")
        return EXIT_ERROR
    return await run(args, path.name, data)


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
