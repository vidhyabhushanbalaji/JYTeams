# JYTeams — Project Context

An Electron desktop app that makes Microsoft Teams project information easier to reach.
**Current focus: the backend only.** Electron is wired up after the backend is done.

## Stack

| Layer | Choice |
| --- | --- |
| Frontend (later) | Electron + Node 24 — `frontend/` is a placeholder today |
| Backend | Python 3.14 + FastAPI — `backend/` |
| Auth | Supabase Auth (bearer token); `AUTH_MODE=dev` trusts `X-Dev-User-Id` locally |
| Data | Supabase **Postgres** (the tree, via `ltree`) + Supabase **Storage** (markdown files) |
| LLM | Gemini via `google-genai` — file and directory summaries, and the navigation that places a new document |
| Graph DB | **None.** Neo4j was retired; Graph AI Search walks the `ltree` hierarchy instead |

## Layout

```text
backend/
├─ app/
│  ├─ main.py              # app factory, lifespan, CORS, mounts the section routers
│  ├─ core/                # config (pydantic-settings), logging, auth dependency
│  ├─ db/                  # Supabase client factories + health ping
│  ├─ health/              # /health, /health/supabase
│  ├─ graph_creation/      # SECTION — implemented (upload a directory → described tree)
│  ├─ graph_add/           # SECTION — implemented (place one document in that tree)
│  └─ graph_ai_search/     # SECTION — implemented (search the tree's summaries)
├─ tests/                  # cross-cutting tests (health, config, wiring)
├─ requirements.txt        # runtime deps (pinned)
├─ requirements-dev.txt    # -r requirements.txt + pytest / ruff / httpx2
├─ pyproject.toml          # pytest + ruff configuration only
└─ .env.example            # every supported env var
supabase/
└─ migrations/             # SQL schema, applied with the Supabase CLI or SQL editor
```

Sections are mounted at `/api/graph-creation`, `/api/graph-add`, `/api/graph-ai-search`.

## Graph Creation, in one paragraph

An upload is a directory of markdown files (loose multipart parts carrying relative
paths, or a single `.zip`). The tree is validated and pruned (empty directories are
dropped; a *leaf* is just a directory with no child directories), then summarised
bottom-up: every file gets a 1–2 sentence summary, and every directory gets a description
built from its child file summaries and child directory descriptions — so the root
describes the whole project. Rows land in `projects` / `directories` / `files`,
progress in `creation_jobs`, and the blobs in a content-addressed Storage bucket.

## Graph Add, in one paragraph

Adding one document is a two-step wizard on `/api/graph-add`. The upload is summarised, then
the tree is walked from the root: only child folders whose description (plus a few names
they hold) aligns with that summary are opened, and the walk stops at leaves, at folders
where nothing relates, or when its budget runs out — those nodes are the candidates. One
consolidation call ranks them, and the project root is always offered. The user picks a
folder and either drops the file there or creates a new folder at that point; the file row
is written, then the affected folder and its ancestors are re-described bottom-up and their
counts refreshed, so the tree keeps the invariant Graph Creation established. The suggestion
is held on an `add_requests` row (24 hours, single use), so placement never re-uploads or
re-summarises, and blobs stay content-addressed so identical documents share one object.

## Graph AI Search, in one paragraph

Search is one read-only endpoint on `/api/graph-ai-search`. The walk starts at the project
root and makes one model call per folder, answering both questions at once: which files
*here* answer the query, and which subfolders could contain an answer. Every matching file is
logged and **every** matching subfolder is opened — there is no expansion budget, so the walk
ends when its frontier is empty and the cost follows how much of the tree the model finds
relevant (`max_directories` is an optional valve that also disables the fallback). If nothing
is logged and the project has at most 40 documents, every folder is swept once, so a vague
description cannot hide a branch. The logged files are then ranked in one consolidation call,
batched when the log is large, because relevance values from separate calls are not
comparable. It reads nothing but the stored summaries and descriptions, writes nothing, and
needs no tables of its own — so a query whose wording appears in no summary cannot be found.

## Commands

All backend commands run from `backend/`, using the repo-root virtualenv:

```powershell
# from backend/
..\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt   # first time only
..\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000   # port taken? use --port 8001
..\.venv\Scripts\python.exe -m pytest
..\.venv\Scripts\python.exe -m ruff check .
..\.venv\Scripts\python.exe -m ruff format .
```

API docs: <http://localhost:8000/docs> · health: <http://localhost:8000/health>

## Conventions

- Python 3.14; start modules with `from __future__ import annotations`.
- `snake_case` for packages/modules, hyphens in URL paths (`/api/graph-ai-search`).
- Configuration only through `app.core.config.get_settings()` — never read `os.environ`
  directly in section code.
- Secrets only in `backend/.env` (git-ignored). Whenever a real key is added, add the
  matching empty placeholder to `backend/.env.example`.
- Shared infrastructure lives in `app/core/`, `app/db/`, `app/health/`; everything else
  belongs to exactly one section.
- Never import another section's internals.
- Uploads are markdown (`.md`, `.markdown`, `.mdx`); anything else is stored but marked
  `summary_status='skipped'` rather than summarised.
- Schema changes are SQL in `supabase/migrations/`, reviewed by both of us before they
  are applied to a shared project.
- **Graph Add is designed and built** — read `backend/README.md` ("Graph Add endpoints")
  before changing its routes, prompts or the `add_requests` shape.
- **Graph AI Search is designed and built** — its walk, the fallback sweep, the optional
  `max_directories` valve and the ranking contract are agreed. Read
  `backend/README.md` ("Graph AI Search endpoints") before changing its routes, prompts or
  `search.py`, and keep it read-only: it must never write to a project.

