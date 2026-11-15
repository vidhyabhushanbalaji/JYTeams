# JYTeams — Project Context

An Electron desktop app that makes Microsoft Teams project information easier to reach.

## Stack

| Layer | Choice |
| --- | --- |
| Frontend | Electron + Node 24 — `frontend/src` (React); Projects, graph, tickets, chat, calendar, settings |
| Backend | Python 3.14 + FastAPI — `backend/` |
| Auth | **A name, no password.** `members` is the identity table; `AUTH_MODE=dev` trusts `X-Dev-User-Id` (a `members.id`) and the app's startup screen signs in by picking or typing a name |
| Data | Supabase **Postgres** (tree via `ltree`, plus `members`, `project_members`, `tickets`, `ticket_files`, `ticket_comments`, `ticket_events`, `chat_messages`, `calendar_events`) + Supabase **Storage** (markdown files) |
| LLM | Gemini `gemini-3.1-flash-lite` (`google-genai`) — **directory descriptions** (creation, and the refresh after a placement) **and one ticket search-terms distillation** (a ticket's wording → the few words a search should use). It is the **only** provider (Groq was retired); `GEMINI_FALLBACK_MODELS` is empty, so every description comes from that model. `SUMMARIZER=mock` gives the offline describer (and the offline distiller). Search and placement ranking are local (`app/core/text.py`) and make no model call |
| Graph DB | **None.** Neo4j was retired; Graph AI Search walks the `ltree` hierarchy instead |

## Layout

```text
backend/
├─ app/
│  ├─ main.py              # app factory, lifespan, CORS, mounts the section routers
│  ├─ core/                # config, logging, auth dependency, text.py, access.py, activity.py
│  ├─ db/                  # Supabase client factories + health ping
│  ├─ health/              # /health, /health/supabase
│  ├─ graph_creation/      # SECTION — implemented (upload a directory → described tree)
│  ├─ graph_add/           # SECTION — implemented (place one document in that tree)
│  ├─ graph_ai_search/     # SECTION — implemented (local search: descriptions + document text)
│  ├─ tickets/             # SECTION — implemented (members, sharing, tickets, cached files, feed)
│  ├─ chat/                # SECTION — implemented (one group chat per project, `@` mentions)
│  └─ calendar/            # SECTION — implemented (project calendars + the merged individual one)
├─ tests/                  # cross-cutting tests (health, config, wiring)
├─ requirements.txt        # runtime deps (pinned)
├─ requirements-dev.txt    # -r requirements.txt + pytest / ruff / httpx2
├─ pyproject.toml          # pytest + ruff configuration only
└─ .env.example            # every supported env var
supabase/
└─ migrations/             # SQL schema, applied with the Supabase CLI or SQL editor
```

Sections are mounted at `/api/graph-creation`, `/api/graph-add`, `/api/graph-ai-search`,
`/api/tickets`, `/api/chat`, `/api/calendar`.

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

## Tickets, in one paragraph

Identity is a name: `POST /api/tickets/members` finds or creates a `members` row and the app
stores that id, so there is no password and no per-person auth user. A project is shared through
`project_members` — `app/core/access.py` is the only place membership is decided, and every
section asks it instead of comparing `owner_id`, which now means "creator". Tickets belong to one
project, are assigned to one member, and carry a status, priority, due date, labels and comments;
the box that marks one complete also stamps who did it. A search is a bad query away from finding
nothing — a ticket is mostly words no document contains — so opening one first distils its title
and description into a short search query (`app/tickets/distill.py`, one model call, `SUMMARIZER=mock`
gives the offline one), then runs Graph AI Search once with five hits and stores both on the ticket
row with two fingerprints: the terms (title + description + `DISTILLER_VERSION`) and the result
(distilled query + context + project's file count and newest `files.updated_at` + limit + folder
threshold + matcher version). A second open is a database read, a project change re-runs only the
model-free search, and `?refresh=true` re-runs the search without asking the model again. Documents
can be attached to a ticket (an existing one, or one placed with the ticket as extra placement
context) without completing it. Every action writes a `ticket_events` row through
`app/core/activity.py`, including project-level changes that came from another section, and the
app's tickets page shows that feed.

## Chat, in one paragraph

A project **is** its group chat: `chat_messages.project_id` is the channel, so there is nothing to
create or backfill, sharing a project joins you to its chat, and access is the same
`ProjectAccess` check every section uses. A message may mention a document, a folder, a ticket or a
calendar event; the composer writes `@[label](file|directory|ticket|event:<uuid>)` into the text
and the backend parses it, checks every id belongs to *that* project (a foreign one is a `400`), and
stores the resolved set on the row (`mentions jsonb`, denormalised so a rename cannot break a chip).
`app/core/mentions.py` holds the marker grammar (the calendar's event notes write the same syntax;
`app/chat/mentions.py` is just chat's import site). The desktop app polls
`GET /api/chat/projects/{id}/messages?after_seq=<last seq>` every ~3 s while the chat is visible —
there is no socket, no new dependency and no model call. Pressing a chip opens the project graph on
that file or folder (the directory case of `GraphFocus`), the tickets screen on that ticket, or the
calendar on that event's day. The reverse direction exists too: a calendar event's **Message in
chat** and a ticket's **Discuss in chat** open the composer with the matching marker pre-filled.
A delete is a soft delete (`[deleted]`) by the author or the project owner, so the cursor never gaps.

## Calendar, in one paragraph

Two calendars, one shape. A project calendar (`GET /api/calendar/projects/{id}`) shows that
project's events plus **every** ticket deadline in it; the individual calendar
(`GET /api/calendar/personal`) merges every project the caller is in — their personal events,
those projects' events, and **only the deadlines of tickets assigned to them**. An event with
`project_id` is a project event (all members see it, only its creator may edit or delete it);
without one it is personal. An event's `notes` may mention a document, a folder or a ticket with the
same `@[label](kind:id)` markers chat uses: they are validated against the event's project when it
is written, stored resolved on the row (`calendar_events.mentions`, migration 0007) and drawn as
chips; `GET /projects/{id}/mention-targets` feeds the picker and
`GET /projects/{id}/mentioning/{kind}/{target_id}` is what a ticket panel reads to list the events
that mention it. `app/calendar/public.py` exposes events as mention targets to chat, and is the only
module another section may import. Deadlines are never copied into a calendar table: they are read
from `tickets.due_date` through `app/tickets/public.py` on every request, so a ticket edit moves its
deadline immediately and a `done` ticket stops appearing. Items sit on the day they start, all-day
events are stored at UTC midnight so their day is timezone-stable, and no model is called.

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
- **Descriptions are prose.** Both prompts ask for natural language without hyphens, underscores
  or run-together identifiers, and `clip_description` naturalises every stored description
  (`naturalise_description`; text in backticks and URLs is preserved). Matching is
  separator-blind: `app/core/text.py` splits `-`, `_`, dashes and camelCase, and also indexes a
  compound's glued form — so a query for `rollback plan` finds `rollback-plan.md`, and the phrase
  bonus sees through the separator. `ScoreConfig.version` is `local-2`; bump it when ranking
  changes. Old descriptions can be rewritten in place with
  `app.graph_creation.tools.normalise_descriptions` (no model call).
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
- **Tickets are designed and built** — read `backend/README.md` ("Tickets endpoints") before
  changing its routes, tables or the cache. The section makes exactly **one** kind of model call:
  `distill.py`, which reduces a ticket's wording to its search terms, is cached on the ticket row
  and is never allowed to block a ticket from opening (no key, `SUMMARIZER=mock` and any model
  failure fall back to `cache.search_query`). A ticket's files are still a cached, model-free
  Graph AI Search; `cache.py`'s two fingerprints (terms: title + description + `DISTILLER_VERSION`;
  results: distilled query + context + file count + newest `files.updated_at` + limit + threshold +
  matcher version) are what make each cache safe to reuse. Bump `MATCHING_VERSION` with
  `ScoreConfig.version` when ranking changes, and `DISTILLER_VERSION` when the prompt or the
  distiller changes.
- **Chat and Calendar are designed and built and call no model.** Read `backend/README.md` ("Chat
  endpoints", "Calendar endpoints") before touching them. The `@` marker grammar is shared
  (`app/core/mentions.py`); chat resolves and validates mention ids against the message's project
  at post time (never trust a client-sent label) and keeps deleted rows so the `seq` poll cursor
  never gaps. An event's notes use the same markers, validated against the event's project and
  stored resolved in `calendar_events.mentions`, so a ticket can list the events that mention it.
  Cross-section reads go through the agreed public modules — `app/calendar/public.py` (events as
  mention targets), `app/graph_creation/public.py`, `app/tickets/public.py` — never another
  section's internals. The calendar never copies a deadline: it reads `tickets.due_date` through
  `app/tickets/public.py`, and only `ProjectAccess` decides who sees which project event.
- **Membership is decided in `app/core/access.py`.** Sections ask `ProjectAccess` for the
  caller's role; `projects.owner_id` is only the creator. Do not reintroduce `owner_id`
  comparisons for access, and do not give another section its own sharing rules.
- **Never import another section's internals.** Use its `public.py` (Graph AI Search, Graph Add)
  or its HTTP API; shared writes such as the activity feed live in `app/core/`.

