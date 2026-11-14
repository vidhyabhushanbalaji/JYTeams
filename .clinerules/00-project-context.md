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
| LLM | Gemini via `google-genai` — file and directory summaries |
| Graph DB | **None.** Neo4j was retired; re-add it only if Graph AI Search needs traversal |

## Layout

```text
backend/
├─ app/
│  ├─ main.py              # app factory, lifespan, CORS, mounts the section routers
│  ├─ core/                # config (pydantic-settings), logging, auth dependency
│  ├─ db/                  # Supabase client factories + health ping
│  ├─ health/              # /health, /health/supabase
│  ├─ graph_creation/      # SECTION — designed and implemented (see its README section)
│  ├─ graph_add/           # SECTION — scaffold only (empty router)
│  └─ graph_ai_search/     # SECTION — scaffold only (empty router)
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
- **Graph Add and Graph AI Search are not designed yet.** Do not invent their endpoints,
  schemas or prompts; agree the design first.

