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

1. **Schema** — apply [`../supabase/migrations/0001_graph_creation.sql`](../supabase/migrations/0001_graph_creation.sql)
   either by pasting it into the dashboard SQL editor, or with the CLI:
   `npx supabase link --project-ref <ref>` then `npx supabase db push`.
   It creates `projects`, `directories`, `files`, `creation_jobs`, enables `ltree` and
   adds row level security policies.
2. **Storage** — create a **private** bucket named `project-files` (Storage → New bucket),
   or point `STORAGE_BUCKET` at whatever you call it.
3. **Auth** — for real tokens set `AUTH_MODE=supabase`. `AUTH_MODE=dev` (the default)
   trusts the `X-Dev-User-Id` header, which is what you want while Supabase Auth is not
   wired into the frontend yet.

With an empty `.env` the API still starts: `/health` works, `/health/supabase` reports
`503`, and section endpoints answer `503` instead of crashing.

## Run

```powershell
..\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```

> **If the port is taken** (`ERROR: [WinError 10013]` / `[WinError 10048]`), another
> process already owns it - on this machine a different project's API sits on 8000.
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
# a whole directory, zipped
Compress-Archive -Path .\docs\* -DestinationPath .\docs.zip
curl.exe -X POST http://localhost:8000/api/graph-creation/uploads `
  -F "mode=new" -F "name=Docs" -F "files=@docs.zip"

# or loose files that carry their relative paths
curl.exe -X POST http://localhost:8000/api/graph-creation/uploads `
  -F "mode=new" -F "name=Docs" `
  -F "files=@README.md;filename=README.md" `
  -F "files=@docs/api/auth.md;filename=docs/api/auth.md"

curl.exe http://localhost:8000/api/graph-creation/jobs/<job_id>
```

## Try it locally (upload a directory)

`app/graph_creation/tools/upload_directory.py` uploads a folder and prints the tree:

```powershell
# preview only: validate the folder and show the tree + bottom-up order, no network
..\.venv\Scripts\python.exe -m app.graph_creation.tools.upload_directory ..\..\docs --dry-run

# real upload against a running API, then print what was stored
..\.venv\Scripts\python.exe -m app.graph_creation.tools.upload_directory ..\..\docs --url http://127.0.0.1:8001 --name Docs

# extend an existing project
..\.venv\Scripts\python.exe -m app.graph_creation.tools.upload_directory ..\..\docs --mode add --project-id <uuid>
```

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
├─ graph_add/         # SECTION — empty scaffold, design TBD
└─ graph_ai_search/   # SECTION — empty scaffold, design TBD
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
| `GEMINI_API_KEY`, `GEMINI_MODEL` | Summarisation (and later Graph AI Search) |
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
