# JYTeams backend

FastAPI service for the JYTeams desktop app. Python 3.14, **Supabase** for auth, Postgres
(the project tree) and file storage, **Gemini** for summaries.

## Setup

Dependencies live in the repo-root virtualenv (`../.venv`, already created with Python
3.14). Every command below runs from `backend/`.

```powershell
..\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
Copy-Item .env.example .env    # then fill in the Supabase / Gemini values
```

Then prepare Supabase:

1. **Schema** — apply
   [`../supabase/migrations/0001_graph_creation.sql`](../supabase/migrations/0001_graph_creation.sql)
   and [`../supabase/migrations/0002_graph_add.sql`](../supabase/migrations/0002_graph_add.sql)
   either by pasting them into the dashboard SQL editor, or with the CLI:
   `npx supabase link --project-ref <ref>` then `npx supabase db push`.
   The first creates `projects`, `directories`, `files`, `creation_jobs`, enables `ltree`
   and adds row level security policies; the second adds `add_requests` for Graph Add.
2. **Storage** — create a **private** bucket named `project-files` (Storage → New bucket),
   or point `STORAGE_BUCKET` at whatever you call it.
3. **Auth** — for real tokens set `AUTH_MODE=supabase`. `AUTH_MODE=dev` (the default)
   trusts the `X-Dev-User-Id` header, which is what you want while Supabase Auth is not
   wired into the frontend yet.
   In dev mode that id must be a **real** Supabase user (Authentication -> Users -> Add user,
   copy the UUID into `DEV_USER_ID`): `projects.owner_id` references `auth.users`, so a
   made-up id fails with a foreign-key error (`23503`).

With an empty `.env` the API still starts: `/health` works, `/health/supabase` reports
`503`, and section endpoints answer `503` instead of crashing.

## Run

```powershell
..\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```

> **If the port is taken** (`ERROR: [WinError 10013]` / `[WinError 10048]`), another
> process already owns it (another project's API has squatted on 8000 here before).
>
> Find the owner with `netstat -ano | Select-String ':8000'` (last column is the PID),
> then either stop that process or pick another port:
>
> ```powershell
> ..\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8001
> ```
>
> A port can also be unusable while Windows still holds a stale socket after a killed
> process - use another one rather than fighting it.

| URL | Purpose |
| --- | --- |
| <http://localhost:8000/docs> | Swagger UI (try the upload straight from here) |
| `/` | API name / version |
| `/health` | Liveness (always 200) |
| `/health/supabase` | Supabase reachability |

## Graph Creation endpoints

All are mounted under `/api/graph-creation` and require an identity (bearer token, or
`X-Dev-User-Id` in dev mode).

| Method | Path | Purpose |
| --- | --- | --- |
| `POST` | `/uploads` | Upload a markdown directory → `202 {project_id, job_id, total_files}` |
| `GET` | `/jobs/{job_id}` | Progress: `queued → summarising → persisting → ok / partial / failed` |
| `GET` | `/projects` | Your projects |
| `GET` | `/projects/{project_id}` | One project (name + whole-project description) |
| `GET` | `/projects/{project_id}/tree?depth=N` | Nested tree with descriptions and file summaries |
| `GET` | `/directories/{directory_id}` | One directory + its immediate children |

`POST /uploads` form fields:

| Field | Meaning |
| --- | --- |
| `files` | One or more `.md` files whose **filename is the relative path** (`docs/api/auth.md`), or a single `.zip` |
| `mode` | `new` (default) builds a new tree — use it for a re-upload too; `add` extends an existing project |
| `name` | Project name, `mode=new` only |
| `project_id` | Target project, required for `mode=add` |

```powershell
# a whole directory, zipped (zip the contents, not the folder, to keep the tree flat)
Compress-Archive -Path .\test_docs\* -DestinationPath .\test_docs.zip
curl.exe -X POST http://localhost:8000/api/graph-creation/uploads `
  -F "mode=new" -F "name=Docs" -F "files=@test_docs.zip"

# or loose files that carry their relative paths
curl.exe -X POST http://localhost:8000/api/graph-creation/uploads `
  -F "mode=new" -F "name=Docs" `
  -F "files=@test_docs/README.md;filename=README.md" `
  -F "files=@test_docs/docs/architecture.md;filename=docs/architecture.md"

curl.exe http://localhost:8000/api/graph-creation/jobs/<job_id>
```

## Graph Add endpoints

All are mounted under `/api/graph-add` and require an identity (bearer token, or
`X-Dev-User-Id` in dev mode). Adding a document is a two-step wizard: suggest, then place.

| Method | Path | Purpose |
| --- | --- | --- |
| `POST` | `/suggestions` | Upload one markdown document → ranked places it could go |
| `POST` | `/placements` | Commit the user's choice (that directory, or a new folder under it) |
| `GET` | `/suggestions/{request_id}` | Re-read the suggestions that were shown |

`POST /suggestions` (multipart): `file` — a single `.md`/`.markdown`/`.mdx`; `project_id` —
the tree to extend. The response carries `request_id`, the document `summary`, and up to
three ranked `suggestions` plus the project root, each with `score`, `reason`,
`proposed_new_directory_names`, `name_available`, `suggested_file_names` (free names when
the uploaded name clashes) and `identical_content_at` (paths holding the same bytes).
`traversal` reports what the walk cost and whether it had to stop early (`degraded`,
`budget_exhausted`).

`POST /placements` (JSON):

| Field | Meaning |
| --- | --- |
| `request_id` | From the suggestion response (expires after 24 hours, single use) |
| `directory_id` | The suggestion the user picked (or the root) |
| `placement` | `direct` puts the file in that directory; `new_directory` creates a folder under it |
| `new_directory_name` | Folder name, required for `new_directory` |
| `file_name` | Optional rename, used to resolve a clash |

Errors: `400` bad name/empty upload, `404` unknown or unowned project/directory/request,
`409` a path already exists (with `suggested_names`) or the suggestion was already used,
`410` the suggestion expired, `415` not markdown, `502` the model could not summarise the
document.

Duplicates are allowed: the same bytes may live at several paths, because blobs are
content-addressed — only an identical `(project_id, path)` is a conflict.

### How a document is placed

1. **Summary** — the document is summarised exactly like a Graph Creation file.
2. **Walk** (`navigate.py`) — starting at the root, the model judges which child folders
   relate to the summary, seeing each folder's description, a few names it contains, and its
   counts; only the matching ones are opened. A node becomes a *candidate* when it is a leaf,
   when none of its children relate, or when the budget is spent. Bounded by
   `MAX_EXPANSIONS` (8) calls, `MAX_BRANCH` (3) children per node and `MAX_CANDIDATES` (3)
   results.
3. **Rank** — one consolidation call orders the shortlist, because scores from separate
   calls are not comparable. The root is always offered as a last option.
4. **Place** — every check runs first, so a rejected placement writes nothing; then the file
   row is written (creating the folder first if asked), and the affected directory and its
   ancestors are re-described bottom-up and their child counts refreshed, so the tree keeps
   the invariant Graph Creation established.

The uploaded bytes and the suggestions are held on an `add_requests` row between the two
steps, so placement never re-uploads or re-summarises the document. Without a
`GEMINI_API_KEY` a deterministic mock navigator is used (keyword overlap, same code paths),
which is also what the tests exercise.

## Graph AI Search endpoints

Mounted under `/api/graph-ai-search`. One read endpoint: it walks the project tree for a query
and returns the documents that answer it, ranked. **Nothing is written**, so it is safe to call
repeatedly.

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/projects/{project_id}/search?q=…` | Ranked documents that answer the query |

| Query param | Default | Meaning |
| --- | --- | --- |
| `q` | — | What you are looking for (3–500 characters after trimming) |
| `limit` | `8` | Results to return (1–25) |
| `min_score` | `0.0` | Drop hits below this score |
| `max_directories` | *(unset)* | Optional valve: stop after opening this many folders. Unset means the walk runs until its frontier is empty |

```json
{
  "query": "how do I roll back a bad production release",
  "project_id": "014c45b7-…",
  "results": [
    {
      "file_id": "ff230d49-…",
      "name": "rollback-deployment.md",
      "path": "guides/rollback-deployment.md",
      "directory_id": "dd473be5-…",
      "directory_path": "guides",
      "summary": "This document provides a step-by-step guide for performing a Helm rollback…",
      "score": 0.92,
      "reason": "This guide provides a direct, step-by-step procedure for performing a Helm rollback in a production environment."
    }
  ],
  "opened_directories": ["", "guides"],
  "traversal": {
    "directories_visited": 2, "directories_opened": 2, "documents_considered": 6,
    "fallback_used": false, "degraded": false, "budget_exhausted": false,
    "model": "gemini-3.5-flash-lite"
  }
}
```

Errors: `400` query too short/long or a numeric parameter out of range, `404` unknown or
unowned project, `409` project has no tree, `502` the model could not search, `503` Supabase
not configured.

### How a search runs

1. **Walk** (`search.py`) — start at the root. One model call per folder answers both
   questions at once: which files *here* answer the query, and which subfolders could contain
   an answer. Every matching file is logged; every matching subfolder is opened. **There is no
   expansion budget** — the walk ends when the frontier is empty, so cost follows how much of
   the tree the model finds relevant. Folders are presented with their description plus a few
   names they hold, because a vague description would otherwise hide a relevant branch.
2. **Fallback** — if the walk logs nothing *and* the project has at most 40 documents, every
   folder is swept once, so a folder whose description happens to be generic cannot hide its
   files. `fallback_used` reports it. The `max_directories` valve disables the sweep — a
   bounded request must not turn into an unbounded one.
3. **Rank** — one consolidation call orders the logged files (`RANK_BATCH` = 25, at least the
   maximum `limit`, so trimming never loses a rankable document). Larger logs are ranked in
   batches and the winners are consolidated, because scores from separate calls are not
   comparable. A failed folder call marks the response `degraded` and skips that subtree; a
   failed ranking falls back to per-folder relevance. The route still answers `200` in both
   cases, which is what happens when the model's quota runs out.

Search runs on the stored summaries and descriptions — the documents themselves are never
read. A query whose wording is absent from every summary cannot be found; that is the
trade-off of using the tree as the index.

### Check it without a quota

```powershell
# offline: the PulseAPI example tree, real stored summaries, mock searcher
..\.venv\Scripts\python.exe -m app.graph_ai_search.tools.verify_search

# live, read-only, against a real project (needs SUPABASE_* and GEMINI_API_KEY)
..\.venv\Scripts\python.exe -m app.graph_ai_search.tools.verify_search_live `
  --project-id <uuid> --user <owner-uuid> [--only rollback] [--limit 5]
```

`verify_search` seeds the exact example tree from the database (six documents), runs five
queries plus a negative control, and asserts the expected document comes back in the top two.
`verify_search_live` does the same through the real route against a real project — search
never writes, so it is safe to run any time. Both print one `ok`/`FAIL` line per assertion and
exit non-zero on failure.

## Try it locally (add one document)

`app/graph_add/tools/add_file.py` drives the two routes the way the wizard does: it prints
the ranked places the document could go, asks which one to use and whether to create a
folder there, then commits the choice.

```powershell
# preview only: validate the file and show what would be sent, no network
..\.venv\Scripts\python.exe -m app.graph_add.tools.add_file ..\..\notes\auth.md --dry-run

# live, interactive: pick a suggestion, then direct or new folder
..\.venv\Scripts\python.exe -m app.graph_add.tools.add_file ..\..\notes\auth.md --project-id <uuid>

# unattended: take suggestion 1 and put the file in that folder
..\.venv\Scripts\python.exe -m app.graph_add.tools.add_file ..\..\notes\auth.md --project-id <uuid> --choose 1 --placement direct

# create a folder at the chosen point; a name clash is resolved by the API's suggestion
..\.venv\Scripts\python.exe -m app.graph_add.tools.add_file ..\..\notes\auth.md --project-id <uuid> --choose 1 --placement new_directory --new-directory-name authentication --auto-rename
```

Options: `--url`, `--project-id`, `--choose`, `--directory-id`, `--root`, `--placement`,
`--new-directory-name`, `--file-name`, `--auto-rename`, `--token`, `--user`, `--timeout`,
`--show-tree`, `--depth`, `--dry-run`, `--json`, `--full`.

Any selection flag makes the run unattended — it never blocks on input. Exit codes: `0`
placed, `1` error, `2` name conflict (alternatives are printed), `3` the suggestion expired,
`130` nothing was written because the question was left unanswered. `--show-tree` prints the
project afterwards using Graph Creation's read route.

### Check the routes without a server

`app/graph_add/tools/verify_add_document.py` is an executable check of the two routes: it
starts the real app in-process (in-memory repository, offline navigator), seeds a project
that already contains files, then asserts the whole journey — suggestions, the walk, both
placement modes, conflicts and renames, single use, expiry and ownership — printing one
`ok`/`FAIL` line per assertion, then exiting non-zero if anything failed.

```powershell
# from backend/ — no Supabase, no Gemini, no .env needed
..\.venv\Scripts\python.exe -m app.graph_add.tools.verify_add_document
..\.venv\Scripts\python.exe -m app.graph_add.tools.verify_add_document --json
```

`--json` also dumps the payloads and the final tree. On Unix it is executable as
`./app/graph_add/tools/verify_add_document.py` (with the virtualenv active). It needs
`AUTH_MODE=dev`, because it identifies itself the same way the dev header does.

### Check against a real project

`app/graph_add/tools/verify_add_document_live.py` does the same journey against a real
project: it starts the app in-process (real Supabase repository, Storage and Gemini) and
drives both routes, asserting the transcript before and after.

```powershell
# suggestions only: nothing is written
..\.venv\Scripts\python.exe -m app.graph_add.tools.verify_add_document_live `
  --project-id <uuid> --user <owner-uuid> --document ..\notes\rollback.md --suggest-only --expect guides

# place it where the walk suggests
..\.venv\Scripts\python.exe -m app.graph_add.tools.verify_add_document_live `
  --project-id <uuid> --user <owner-uuid> --document ..\notes\rollback.md
```

This one **writes**: one `files` row, one Storage object (content-addressed, so a duplicate
document adds none) and a re-description of the target folder, its ancestors and the project
— those are billed model calls. `--directory <path|id>` overrides the suggestion,
`--placement new_directory --new-directory-name <name>` creates a folder first, `--file-name`
resolves a clash, and `--json` dumps every payload. Exit codes: `0` placed, `1` a check
failed, `2` the name is taken.

> If Gemini answers `429 RESOURCE_EXHAUSTED`, the free-tier daily quota for that model is
> spent. `GEMINI_MODEL=gemini-3.5-flash-lite` (a process-only override) usually still has
> quota; the summaries stored on the project name the model that produced them.

## Try it locally (upload a directory or a .zip)

`app/graph_creation/tools/upload_directory.py` uploads a folder (as loose multipart parts)
or a single `.zip` (one part, which the API expands) and prints the tree:

```powershell
# preview only: validate the input and show the tree + bottom-up order, no network
..\.venv\Scripts\python.exe -m app.graph_creation.tools.upload_directory ..\test_docs --dry-run

# real upload against a running API, then print what was stored
..\.venv\Scripts\python.exe -m app.graph_creation.tools.upload_directory ..\test_docs --name Docs

# the same folder as a .zip - one HTTP part instead of one part per file
..\.venv\Scripts\python.exe -m app.graph_creation.tools.upload_directory ..\test_docs.zip --name Docs

# extend an existing project
..\.venv\Scripts\python.exe -m app.graph_creation.tools.upload_directory ..\test_docs --mode add --project-id <uuid>
```

> `Compress-Archive -Path .\test_docs` stores every entry under `test_docs/`, which becomes
> an extra top-level folder in the graph. Zip the contents (`.\test_docs\*`) to get the same
> tree as a directory upload.

Options: `--url`, `--mode new|add`, `--name`, `--project-id`, `--token` (Supabase
bearer token; otherwise the `X-Dev-User-Id` header is sent), `--depth`, `--timeout`,
`--interval`, `--json`, `--full`.

`--dry-run` uses the offline mock summariser; a live run uses Gemini when
`GEMINI_API_KEY` is set. Either way the tree structure - empty-directory pruning,
natural ordering, `ltree` paths - is identical to what the API stores.

## How the tree is built

1. **Ingest** (`ingest.py`) — expands a zip or reads the multipart parts; rejects `..`,
   absolute paths, oversized files and encrypted archives.
2. **Tree** (`tree.py`) — builds the hierarchy, **drops empty directories**, sorts
   children case-insensitively and number-aware (`file2` before `file10`), and projects
   each path onto a sanitised `ltree` label (suffixes keep siblings unique).
3. **Summarise** (`summarise.py`, `service.py`) — post-order: each file gets 1–2 sentences
   from Gemini, then each directory is described from its child file summaries and child
   directory descriptions, so the root describes the whole project.
   `SUMMARIZER=auto` uses Gemini when `GEMINI_API_KEY` is set, otherwise a deterministic
   offline mock — the pipeline runs (and tests pass) with no key and no network.
4. **Persist** (`repository.py`, `storage.py`) — blobs go to Storage under
   `{project_id}/{sha256}.md` (content-addressed: identical content is stored once, but
   every path still gets its own row), then `directories` are inserted one level at a time
   so parent ids exist, then `files`.

`mode=add` merges into the existing tree: existing directory paths are reused, new files
are attached, then every affected ancestor (deepest first) is re-described and its child
counts refreshed. Uploaded paths that already exist are rejected with `409`.

## Test & lint

```powershell
..\.venv\Scripts\python.exe -m pytest
..\.venv\Scripts\python.exe -m ruff check .
..\.venv\Scripts\python.exe -m ruff format .
```

The suite is hermetic — settings are blanked, auth runs in dev mode, and the section tests
use an in-memory repository, an in-memory object store and the mock summariser. Nothing
touches Supabase, Gemini or the network.

## Structure

```text
app/
├─ main.py            # app factory, lifespan, CORS, mounts the section routers
├─ core/config.py     # Settings (pydantic-settings) — the only place env vars are read
├─ core/auth.py       # get_current_user (dev header or Supabase bearer token)
├─ db/supabase.py     # admin_client() / anon_client(), reachability ping
├─ health/router.py
├─ graph_creation/    # SECTION — implemented
│  ├─ router.py       # HTTP surface
│  ├─ service.py      # orchestration: summarise → persist, add-mode merge, reads
│  ├─ tree.py         # validation, pruning, ordering, ltree paths
│  ├─ ingest.py       # multipart / zip parsing and limits
│  ├─ extract.py      # markdown → prompt text
│  ├─ summarise.py    # Gemini + mock summarisers
│  ├─ storage.py      # Supabase Storage, content-addressed keys
│  ├─ repository.py   # PostgREST access (protocol + Supabase implementation)
│  └─ tests/
├─ graph_add/         # SECTION — implemented
│  ├─ router.py       # HTTP surface (suggest → place)
│  ├─ service.py      # orchestration, conflicts, ancestor refresh
│  ├─ navigate.py     # bounded semantic walk + ranking contract
│  ├─ llm.py          # Gemini + mock navigators
│  ├─ prompts.py      # navigation / ranking / folder-description prompts
│  ├─ labels.py       # folder + file naming, ltree labels, rename suggestions
│  ├─ extract.py      # markdown → prompt text
│  ├─ storage.py      # content-addressed blob upload
│  ├─ repository.py   # PostgREST access (add_requests + tree writes)
│  └─ tests/
└─ graph_ai_search/   # SECTION — implemented (search the tree's summaries)
```

## Configuration

All settings and defaults live in `app/core/config.py`; env var names are in
`.env.example`. Read them with `get_settings()` — never `os.environ` in section code.

| Variable | Notes |
| --- | --- |
| `APP_ENV`, `LOG_LEVEL`, `API_PREFIX` | Operational defaults |
| `CORS_ORIGINS` | Comma separated (or JSON list); add the Electron origin later |
| `AUTH_MODE`, `DEV_USER_ID` | `dev` trusts `X-Dev-User-Id`; `supabase` verifies the bearer token |
| `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY` | Service role bypasses RLS — server-side only |
| `STORAGE_BUCKET` | Bucket for uploaded markdown (default `project-files`) |
| `GEMINI_API_KEY`, `GEMINI_MODEL`, `GEMINI_THINKING_BUDGET` | Summarisation (and later Graph AI Search). `gemini-3.5-flash-lite` has the most free-tier quota; `gemini-3.5-flash` / `gemini-3.6-flash` answer 429 once it is spent. Use a positive budget (e.g. `512`) - the lite models reject `0` with 400 |
| `SUMMARIZER`, `SUMMARY_MAX_INPUT_CHARS`, `SUMMARY_CONCURRENCY` | `auto` / `gemini` / `mock` |
| `MAX_UPLOAD_FILES`, `MAX_UPLOAD_BYTES`, `MAX_FILE_BYTES`, `MAX_DIRECTORY_DEPTH` | Upload limits |

## Known limitations

- **Background jobs are in-process `asyncio` tasks.** Run a single uvicorn worker; a hard
  crash mid-job leaves that job row unfinished (no partial tree is ever written, because
  every summary is produced before anything is inserted). A real queue is the next step
  if we need durability.
- **The service-role client bypasses RLS,** so ownership is enforced in
  `GraphCreationService` (`_require_project`, `get_job`). The RLS policies in the
  migration protect direct access from the Electron app with a user JWT.
- **`ltree` paths are derived, not authoritative.** The human-readable `path` column is
  what the API returns and what uniqueness is enforced on; `ltree_path` exists for
  subtree queries (`where ltree_path <@ 'docs.api'`).
