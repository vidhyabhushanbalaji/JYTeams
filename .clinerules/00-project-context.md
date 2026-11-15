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
| LLM | Gemini `gemini-3.1-flash-lite` (`google-genai`) — **directory descriptions only** (creation, and the refresh after a placement). It is the **only** provider (Groq was retired); `GEMINI_FALLBACK_MODELS` is empty, so every description comes from that model. `SUMMARIZER=mock` gives the offline describer. Search and placement ranking are local (`app/core/text.py`) and make no model call |
| Graph DB | **None.** Neo4j was retired; Graph AI Search walks the `ltree` hierarchy instead |

## Layout

```text
backend/
├─ app/
│  ├─ main.py              # app factory, lifespan, CORS, mounts the section routers
│  ├─ core/                # config (pydantic-settings), logging, auth dependency, text.py
│  ├─ db/                  # Supabase client factories + health ping
│  ├─ health/              # /health, /health/supabase
│  ├─ graph_creation/      # SECTION — implemented (upload a directory → described tree)
│  ├─ graph_add/           # SECTION — implemented (place one document in that tree)
│  └─ graph_ai_search/     # SECTION — implemented (local search: descriptions + document text)
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
dropped; a *leaf* is just a directory with no child directories), then described
bottom-up: each folder's description is written from the **text** of the files directly
inside it plus its child folder descriptions — so the root describes the whole project and
the import costs one model call per folder, not one per file. Documents are never summarised
(`summary_status='skipped'`). Rows land in `projects` / `directories` / `files`, progress in
`creation_jobs`, and the blobs in a content-addressed Storage bucket. Two further endpoints
read and save a document's own markdown (`GET`/`PUT /files/{id}/content`); a save writes a new
content-addressed object and repoints the row, makes **no model call**, and takes an optional
`expected_sha256` so a stale window gets a 409 instead of overwriting a newer edit.

## Graph Add, in one paragraph

Adding one document is a two-step wizard on `/api/graph-add`. The document is reduced to its
title, filename and most frequent terms, and **every** folder is scored against that query
locally (`navigate.py`, `scoring.py` — same weights as search, no model call), so a vague
parent cannot hide a matching child; the best three are offered and the project root always
last. The user picks a folder and either drops the file there or creates a new folder at that
point; the file row is written, then **one** model call updates the descriptions of the new
folder (if any), the folder that received the file and its ancestors, and their counts are
refreshed — so the tree keeps the invariant Graph Creation established. The suggestion is
held on an `add_requests` row (24 hours, single use), so placement never re-uploads the
document, and blobs stay content-addressed so identical documents share one object.

## Graph AI Search, in one paragraph

Search is one read-only endpoint on `/api/graph-ai-search`, and it calls no model. The walk
starts at the project root; each folder is scored locally from its description, name and a few
names it holds, and only folders clearing `SCORING_FOLDER_THRESHOLD` are opened. The documents
directly inside every opened folder are read from Storage and scored against their own text,
which is what produces `matched_terms` and the `excerpt` — reads are cached by content hash and
bounded by `SEARCH_MAX_FILES_READ`. If the best match is weak and the project has at most 40
documents, every folder is swept once so a generic description cannot hide its files
(`max_directories` is an optional valve that also disables the sweep). Ranking is one sort,
because every score comes from the same function; unreadable documents mark the response
`degraded` instead of failing it. It writes nothing and needs no tables of its own. Matching is
lexical (stems, names, phrase bonuses), so a query phrased in words the documentation never
uses can still miss.

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
- Uploads are markdown (`.md`, `.markdown`, `.mdx`). Documents are never summarised: every
  `files` row is `summary_status='skipped'`, and a non-markdown upload is stored without its
  text reaching a prompt.
- Folder descriptions are capped at `DESCRIPTION_MAX_CHARS` (300 characters, clipped after the
  call as well as asked for in the prompt), and model calls start at least
  `LLM_MIN_INTERVAL_SECONDS` (2 s) apart — retries and fallback models included.
- Schema changes are SQL in `supabase/migrations/`, reviewed by both of us before they
  are applied to a shared project.
- **Gemini is the only model provider** (`gemini-3.1-flash-lite`), and anything that can reach
  the model for real is capped at **5 requests per AI-run task** — read
  `.clinerules/20-ai-usage-limits.md` before running a live check. Users of the app are not
  limited (for now).
- **Graph Add is designed and built** — read `backend/README.md` ("Graph Add endpoints")
  before changing its routes, prompts or the `add_requests` shape. Keep suggestions local
  (`scoring.py`, `navigate.py`: no model call) and keep placement to **one** description call
  (`describer.py`); a suggestion must stay single-use and 24 hours.
- **Graph AI Search is designed and built** — the local walk, the weak-match sweep, the
  optional `max_directories` valve and the shared scoring weights are agreed. Read
  `backend/README.md` ("Graph AI Search endpoints") before changing its routes or `search.py`,
  and keep it read-only and model-free: it must never write to a project and never call a
  model.

