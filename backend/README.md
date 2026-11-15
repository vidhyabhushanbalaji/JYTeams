# JYTeams backend

FastAPI service for the JYTeams desktop app. Python 3.14, **Supabase** for auth, Postgres
(the project tree) and file storage, and **Gemini** (`gemini-3.1-flash-lite`) for folder
descriptions.

## Setup

Dependencies live in the repo-root virtualenv (`../.venv`, already created with Python
3.14). Every command below runs from `backend/`.

```powershell
..\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
Copy-Item .env.example .env    # then fill in the Supabase / Gemini values
```

Then prepare Supabase:

1. **Schema** — apply
   [`../supabase/migrations/0001_graph_creation.sql`](../supabase/migrations/0001_graph_creation.sql),
   [`../supabase/migrations/0002_graph_add.sql`](../supabase/migrations/0002_graph_add.sql),
   [`../supabase/migrations/0003_tickets.sql`](../supabase/migrations/0003_tickets.sql),
   [`../supabase/migrations/0004_ticket_search_terms.sql`](../supabase/migrations/0004_ticket_search_terms.sql),
   [`../supabase/migrations/0005_chat.sql`](../supabase/migrations/0005_chat.sql),
   [`../supabase/migrations/0006_calendar.sql`](../supabase/migrations/0006_calendar.sql)
   and [`../supabase/migrations/0007_calendar_mentions.sql`](../supabase/migrations/0007_calendar_mentions.sql)
   either by pasting them into the dashboard SQL editor, or with the CLI:
   `npx supabase link --project-ref <ref>` then `npx supabase db push`.
   The first creates `projects`, `directories`, `files`, `creation_jobs` and enables `ltree`;
   the second adds `add_requests` for Graph Add; the third **repoints ownership at `members`**
   (a name-only identity), adds `project_members`, `tickets`, `ticket_files`, `ticket_comments`,
   `ticket_events` and `files.updated_at`, and drops the old `auth.uid()` policies (the app talks
   to this API, never to Supabase directly). Every existing owner is seeded as a member with the
   same uuid, so no row is rewritten; the file ends with a rollback block. The fourth adds
   `tickets.search_terms_fingerprint`; the fifth adds `chat_messages`; the sixth adds
   `calendar_events`; the seventh adds `calendar_events.mentions` (the resolved document, folder
   and ticket references an event's notes carry). The last four are additive, with a rollback
   block each.
2. **Storage** — create a **private** bucket named `project-files` (Storage → New bucket),
   or point `STORAGE_BUCKET` at whatever you call it.
3. **Auth** — for real tokens set `AUTH_MODE=supabase`. `AUTH_MODE=dev` (the default)
   trusts the `X-Dev-User-Id` header, which is what you want while Supabase Auth is not
   wired into the frontend yet.
   **Identity is a name, not an auth user.** After migration 0003 the header carries a
   `members.id`: `POST /api/tickets/members {"display_name": "Ada"}` signs in (find-or-create)
   and the desktop app stores that id in its config. The startup screen lists the names that
   already exist. No password and no token is involved — this is a hackathon build, and
   `AUTH_MODE=supabase` is still there if real accounts are wanted later.

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
| `GET` | `/jobs/{job_id}` | Progress: `queued → summarising → persisting → ok / partial / failed` (the `summarising` stage describes folders now; the name is kept for the schema) |
| `GET` | `/projects` | Your projects |
| `GET` | `/projects/{project_id}` | One project (name + whole-project description) |
| `GET` | `/projects/{project_id}/tree?depth=N` | Nested tree with descriptions for every folder |
| `GET` | `/directories/{directory_id}` | One directory + its immediate children |
| `GET` | `/files/{file_id}/content` | One document's markdown: `{id, name, path, size_bytes, content_sha256, text, editable, truncated}` |
| `PUT` | `/files/{file_id}/content` | Save a new body (`{text, expected_sha256?}`); no model is called |

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

### Reading and editing a document

`GET /files/{file_id}/content` returns the stored markdown as text. The desktop app opens it on
a double-click and offers **Edit**, so `PUT /files/{file_id}/content` takes a whole replacement
body:

```powershell
curl.exe http://localhost:8000/api/graph-creation/files/<file_id>/content

curl.exe -X PUT http://localhost:8000/api/graph-creation/files/<file_id>/content `
  -H "Content-Type: application/json" `
  -d "{\"text\":\"# Title`n`nNew body.\",\"expected_sha256\":\"<the digest you read>\"}"
```

- **Blobs are content-addressed and shared**, so a save never rewrites the old object: the new
  text is stored under its own digest and the `files` row is repointed (`size_bytes`,
  `content_sha256`, `storage_path`). A document that shares the old bytes is untouched, and the
  previous object is left in place (like a re-upload, it is simply no longer referenced).
- `expected_sha256` is optional but recommended: when it no longer matches, the save answers
  **409** instead of overwriting a newer edit — that is how two windows cannot clobber each
  other.
- Bodies over `MAX_FILE_BYTES` answer **413**. Non-markdown rows, and documents longer than
  `FILE_EDIT_MAX_CHARS`, come back `editable: false` (the long ones also `truncated: true`).
- **No model call happens.** Folder descriptions stay as they were until the next add or
  placement; search reads document text by digest, so an edited document is found by its new
  words immediately.

## Graph Add endpoints

All are mounted under `/api/graph-add` and require an identity (bearer token, or
`X-Dev-User-Id` in dev mode). Adding a document is a two-step wizard: suggest, then place.
Suggestions are scored locally, so they cost **no model calls**; placement costs exactly one.

| Method | Path | Purpose |
| --- | --- | --- |
| `POST` | `/suggestions` | Upload one markdown document → ranked places it could go |
| `POST` | `/placements` | Commit the user's choice (that directory, or a new folder under it) |
| `GET` | `/suggestions/{request_id}` | Re-read the suggestions that were shown |

`POST /suggestions` (multipart): `file` — a single `.md`/`.markdown`/`.mdx`; `project_id` —
the tree to extend. The response carries `request_id`, the document `preview` (its first ~200
characters — no model wrote it), and up to three ranked `suggestions` plus the project root,
each with `score`, `reason`, `matched_terms`, `proposed_new_directory_names`,
`name_available`, `suggested_file_names` (free names when the uploaded name clashes) and
`identical_content_at` (paths holding the same bytes). `scan` reports what the ranking cost:
`folders_scored`, `threshold` and `scorer_version`.

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
`410` the suggestion expired, `415` not markdown.

Duplicates are allowed: the same bytes may live at several paths, because blobs are
content-addressed — only an identical `(project_id, path)` is a conflict.

### How a document is placed

1. **Scan** (`scoring.py`, `navigate.py`) — the document is reduced to its title, filename and
   its ~40 most frequent terms, and **every** folder in the project is scored against that
   query: description (55%), name (25%) and a few names it holds (20%), using the same weights
   Graph AI Search uses. No model is called — scoring a few hundred folders costs nothing —
   and the scan is exhaustive rather than a walk, so a parent with a vague description cannot
   hide a child that is a perfect match. The best `MAX_CANDIDATES` (3) are offered and the
   project root is always added last.
2. **Place** — every check runs first, so a rejected placement writes nothing; then the file
   row is written (creating the folder first if asked), and **one** model call
   (`describer.py`) updates the affected descriptions: the new folder (if one was created),
   the folder the document landed in, and every ancestor, deepest first. Their child counts
   are refreshed from the same rows, so the tree keeps the invariant Graph Creation
   established. A failed call leaves the existing descriptions in place — a stale description
   is better than a failed placement.

The uploaded bytes and the suggestions are held on an `add_requests` row between the two
steps, so placement never re-uploads the document, and blobs stay content-addressed so
identical documents share one object. Documents are not summarised at all; only the folders
around them are described. Without a model key (or with `SUMMARIZER=mock`) a deterministic
mock describer is used (it names the files and subfolders it sees), which is also what the tests
exercise.

## Graph AI Search endpoints

Mounted under `/api/graph-ai-search`. One read endpoint: it scores the project tree for a
query and returns the documents that answer it, ranked, plus the folders worth browsing.
**No model is called and nothing is written**, so it is cheap to call repeatedly.

Matching is lexical and separator-blind: `-`, `_` and Unicode dashes split a word, camelCase is
split, and a compound name is also indexed as its glued form — so a query for `rollback plan`
finds `rollback-plan.md`, `rollback_plan.md`, `rollbackPlan.md` and a body that says
`rollback-plan`; a query for `rollbackplan` still finds the compound. The exact-phrase bonus is
normalised the same way. Descriptions are stored as plain prose (see "How the tree is built"), so
folder text reads the way people type.

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/projects/{project_id}/search?q=…` | Ranked documents that answer the query |

| Query param | Default | Meaning |
| --- | --- | --- |
| `q` | — | What you are looking for (3–500 characters after trimming) |
| `context` | *(empty)* | Optional extra wording to widen the match (≤500 characters) |
| `limit` | `8` | Results to return (1–25) |
| `min_score` | `0.0` | Drop hits below this score |
| `max_directories` | *(unset)* | Optional valve: stop after opening this many folders |

```json
{
  "query": "how do I roll back a bad production release",
  "context": "",
  "project_id": "014c45b7-…",
  "results": [
    {
      "file_id": "ff230d49-…",
      "name": "rollback-deployment.md",
      "path": "guides/rollback-deployment.md",
      "directory_id": "dd473be5-…",
      "directory_path": "guides",
      "score": 0.71,
      "matched_terms": ["deployment", "release", "rollback"],
      "excerpt": "This document provides a step-by-step guide for performing a Helm rollback…"
    }
  ],
  "directories": [
    {
      "directory_id": "dd473be5-…", "path": "guides", "name": "guides", "depth": 1,
      "score": 0.42, "matched_terms": ["deployment", "release"]
    }
  ],
  "opened_directories": ["", "guides"],
  "traversal": {
    "directories_visited": 2, "directories_opened": 2, "documents_considered": 6,
    "files_read": 3, "fallback_used": false, "degraded": false, "budget_exhausted": false,
    "scorer_version": "local-1", "duration_ms": 41
  }
}
```

Errors: `400` query too short/long, context too long, or a numeric parameter out of range,
`404` unknown or unowned project, `409` project has no tree.

### How a search runs

1. **Walk** (`search.py`) — start at the root. Each folder is scored locally against the query
   (`scoring.py`, the same weights Graph Add uses): the description, the folder name, and a few
   names it holds. A folder clearing `SCORING_FOLDER_THRESHOLD` is opened; the rest are pruned
   without reading anything.
2. **Read** — the documents directly inside every opened folder are read from Storage and
   scored against their own text. `matched_terms` says why one matched and `excerpt` shows
   where; reads are cached by content hash, so identical documents cost one download, and
   `SEARCH_MAX_FILES_READ` bounds a single search.
3. **Fallback** — if the best match is weak (below 0.5) *and* the project has at most 40
   documents, every folder is swept once, so a folder whose description happens to be generic
   cannot hide its files. `fallback_used` reports it; the `max_directories` valve disables the
   sweep, because a bounded request must not turn into an unbounded one.
4. **Rank** — one sort, because every score comes from the same function and is therefore
   comparable (no consolidation call exists any more). A document that cannot be read marks
   the response `degraded` and is skipped; the route still answers `200`.

Search reads folder descriptions to decide *where* to look and document bodies to decide *what*
matched, so it needs no per-file summaries and no model. The trade-off is that matching is
lexical — stemming, phrase and name bonuses help — so a query phrased in words the
documentation never uses will still miss.

### Check it without a quota

```powershell
# offline: the PulseAPI example tree, seeded document text, local scorer (no model call)
..\.venv\Scripts\python.exe -m app.graph_ai_search.tools.verify_search

# live, read-only, against a real project (needs SUPABASE_* and a model key)
..\.venv\Scripts\python.exe -m app.graph_ai_search.tools.verify_search_live `
  --project-id <uuid> --user <owner-uuid> [--only rollback] [--limit 5]
```

`verify_search` seeds the exact example tree (six documents, with their text), runs five
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
starts the real app in-process (in-memory repository, offline describer), seeds a project
that already contains files, then asserts the whole journey — suggestions, the scan, both
placement modes, conflicts and renames, single use, expiry and ownership — printing one
`ok`/`FAIL` line per assertion, then exiting non-zero if anything failed.

```powershell
# from backend/ — no Supabase, no model key, no .env needed
..\.venv\Scripts\python.exe -m app.graph_add.tools.verify_add_document
..\.venv\Scripts\python.exe -m app.graph_add.tools.verify_add_document --json
```

`--json` also dumps the payloads and the final tree. On Unix it is executable as
`./app/graph_add/tools/verify_add_document.py` (with the virtualenv active). It needs
`AUTH_MODE=dev`, because it identifies itself the same way the dev header does.

### Check against a real project

`app/graph_add/tools/verify_add_document_live.py` does the same journey against a real
project: it starts the app in-process (real Supabase repository, Storage and the configured
describer) and drives both routes, asserting the transcript before and after.

```powershell
# suggestions only: nothing is written
..\.venv\Scripts\python.exe -m app.graph_add.tools.verify_add_document_live `
  --project-id <uuid> --user <owner-uuid> --document ..\notes\rollback.md --suggest-only --expect guides

# place it where the scan suggests
..\.venv\Scripts\python.exe -m app.graph_add.tools.verify_add_document_live `
  --project-id <uuid> --user <owner-uuid> --document ..\notes\rollback.md
```

This one **writes**: one `files` row, one Storage object (content-addressed, so a duplicate
document adds none) and a **single** model call that refreshes the descriptions of the target
folder, its ancestors and the project. `--directory <path|id>` overrides the suggestion,
`--placement new_directory --new-directory-name <name>` creates a folder first, `--file-name`
resolves a clash, and `--json` dumps every payload. Exit codes: `0` placed, `1` a check
failed, `2` the name is taken.

> A `429` means the model's quota is spent or it is briefly throttled. The Gemini describer
> retries an overload on the same model and, if `GEMINI_FALLBACK_MODELS` is configured, moves on
> to the next model. The chain is **empty by default**, so every description comes from
> `GEMINI_MODEL` (`gemini-3.1-flash-lite`) and a failure surfaces instead of another model
> quietly writing the text. `description_model` on each folder row names the model that actually
> produced its text.

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

`--dry-run` uses the offline mock describer; a live run uses the Gemini describer
(`GEMINI_MODEL`, `gemini-3.1-flash-lite`) unless `SUMMARIZER=mock` or no `GEMINI_API_KEY` is
configured, in which case it is the mock too.
Either way the tree structure - empty-directory pruning, natural ordering, `ltree` paths - is
identical to what the API stores.

## How the tree is built

1. **Ingest** (`ingest.py`) — expands a zip or reads the multipart parts; rejects `..`,
   absolute paths, oversized files and encrypted archives.
2. **Tree** (`tree.py`) — builds the hierarchy, **drops empty directories**, sorts
   children case-insensitively and number-aware (`file2` before `file10`), and projects
   each path onto a sanitised `ltree` label (suffixes keep siblings unique).
3. **Describe** (`describe.py`, `service.py`) — deepest level first, root last: a parent's
   prompt carries its children's finished descriptions, so the root describes the whole project.
   Each prompt also carries the **text** of the files directly inside the folder (each cut to
   `DESCRIPTION_FILE_HEAD_CHARS`, the folder total capped by `DESCRIPTION_MAX_INPUT_CHARS`).
   **Files are not summarised at all** — one model call per directory — and the prompt asks for
   the words a reader would search for, because a local search matches this text to find the
   folder. It also asks for **plain prose**: no hyphenated, underscored or run-together
   identifiers ("rollback plan", not "rollback-plan"), and every description is naturalised by
   `clip_description` on the way in, so an existing row can be rewritten with
   `app.graph_creation.tools.normalise_descriptions` (no model call; text in backticks and URLs
   is preserved). Folders on the same level have no dependency on each other and run concurrently
   up to `SUMMARY_CONCURRENCY`; progress is reported per folder, so the job moves steadily
   instead of jumping in tens of files. Every description is capped at `DESCRIPTION_MAX_CHARS`
   (300): the prompt asks for that length and the reply is clipped to it, at a word boundary.
   Model calls start at least `LLM_MIN_INTERVAL_SECONDS` (2 s) apart, including retries and
   fallback models. Gemini (`gemini-3.1-flash-lite`) is the only provider; with no
   `GEMINI_API_KEY` (or `SUMMARIZER=mock`) a deterministic offline mock writes the descriptions,
   so the pipeline runs (and tests pass) with no key and no network.
4. **Persist** (`repository.py`, `storage.py`) — blobs go to Storage under
   `{project_id}/{sha256}.md` (content-addressed: identical content is stored once, but
   every path still gets its own row), then `directories` are inserted one level at a time
   so parent ids exist, then `files` (with `summary_status='skipped'`).

A folder whose description failed is stored with `description = NULL` (and the job becomes
`partial`, with the failing paths in `error`) rather than a placeholder that would match every
search. Descriptions are produced before anything is written, so a failed run never leaves a
half-written tree behind.

`mode=add` merges into the existing tree: existing directory paths are reused, new files
are attached, then every affected directory and its ancestors (deepest first) is re-described
from the files' text — read back from Storage for the ones already there — and its child
counts refreshed. Uploaded paths that already exist are rejected with `409`.

## Tickets endpoints

Mounted under `/api/tickets`. Identity is a **name**: signing in finds or creates a member, and
`X-Dev-User-Id` carries that member's id afterwards. A project belongs to the members listed in
`project_members`; `projects.owner_id` is only the creator, and the project list returns the
caller's `role` (`owner` or `member`). Opening a ticket for the first time makes **one model call**
(`app/tickets/distill.py`) that reduces the ticket's own wording to a short search query, then a
cached, model-free Graph AI Search result; see *The file cache* below.

| Method | Path | Purpose |
| --- | --- | --- |
| `POST` | `/members` | Sign in (find-or-create) with `{display_name}` |
| `GET` | `/members` | Every name, for the startup picker / assignee list |
| `GET` | `/me` | The caller as a member; **404** means "pick a name again" |
| `GET` | `/projects/{id}/members` | Who can see a project |
| `POST` | `/projects/{id}/members` | Share with `{member_id}` (owner only) |
| `DELETE` | `/projects/{id}/members/{member_id}` | Stop sharing (owner only; the owner cannot be removed) |
| `GET` | `/tickets?scope=mine\|project&project_id=&status=&limit=` | `mine` (default) is the caller's to-do list; `project` needs a `project_id` |
| `POST` | `/tickets` | Create `{project_id, title, description?, assignee_id?, priority?, due_date?, labels?}` |
| `GET` | `/tickets/{id}?refresh=` | The ticket, its comments **and** its files (runs the cached search once) |
| `PATCH` | `/tickets/{id}` | Only the fields you send; `null` assigns nothing / clears the field |
| `POST` | `/tickets/{id}/status` | `{status: todo\|in_progress\|done}` — completion stamps who and when |
| `GET` | `/tickets/{id}/files?refresh=` | The cached file set (refresh recomputes it) |
| `POST` | `/tickets/{id}/files` | Attach an existing project document: `{file_id, source?}` |
| `DELETE` | `/tickets/{id}/files/{file_id}` | Take a document off the ticket (it stays in the project) |
| `POST` | `/tickets/{id}/comments` | `{body}` |
| `GET` | `/activity?project_id=&ticket_id=&limit=` | Changes and updates; omit `project_id` for every project you can see |

**A ticket's calendar events.** The ticket detail does not embed calendar events, and the tickets
section does not import the calendar: the desktop app asks
`GET /api/calendar/projects/{id}/mentioning/ticket/{ticket_id}` for the events whose notes mention
the ticket and shows them under **On the calendar**. The reverse press — **Discuss in chat** —
just pre-fills the project chat's composer with `@[#12 …](ticket:<uuid>)`, which the chat route
validates like any other mention.

### Why a ticket is distilled first

A ticket is written for people. Graph AI Search scores a query by **term coverage** — the share of
its terms each folder and document contains — so a description full of dates, names, acceptance
criteria and process verbs ("review", "whether", "still") drags every score down and can leave the
walk with nothing to open. One model call reduces the ticket to the words a document about it would
use:

```text
"Review whether decision rights are still accurate"  ->  query: "decision rights accurate"
                                                         points: ["decision rights", "approval authority"]
```

- `app/tickets/distill.py` holds the prompt, the Gemini client and `LocalDistiller` — the offline,
  deterministic reduction used by tests, keyless runs and `SUMMARIZER=mock`. It drops task words
  from a fixed list and keeps the ticket's most frequent content words.
- The call is `temperature: 0`, JSON output (`{"query": …, "terms": […]}`), capped at 200
  characters of query and five points of 60 characters; the points are joined into the search's
  `context` (≤ 500 characters) and clipped again after the reply.
- **A model problem never breaks a ticket.** No key, `SUMMARIZER=mock`, an empty reply, a bad key or
  a timeout all fall back to `cache.search_query` (the title, or the description when the title is
  very short), and the failure is not cached, so the next open tries the model again.

### The file cache (and why reopening a ticket is free)

A ticket's files come from `GET /api/graph-ai-search/projects/{id}/search` with `q` = the distilled
query and `context` = the distilled points, capped at five results. Two caches, with one fingerprint
each, are stored on the ticket row:

| Cache | Fingerprint covers | Re-made when |
| --- | --- | --- |
| the terms (`search_query`, `search_context`) | title · description · `DISTILLER_VERSION` | the ticket's wording changes |
| the results (`search_results`) | distilled query · context · file count · newest `files.updated_at` · limit · `SCORING_FOLDER_THRESHOLD` · `MATCHING_VERSION` · `DISTILLER_VERSION` | the terms change, a document is added or edited, or `?refresh=true` |

- The first time a ticket is opened both run; the second open is a database read.
- A project document added or edited re-runs **only the model-free search**: the words did not
  change, so the model is not asked again. The same is true of `?refresh=true`.
- Raising `MATCHING_VERSION` in `app/tickets/cache.py` (keep it in step with `ScoreConfig.version`)
  invalidates every stored result exactly once; raising `DISTILLER_VERSION` (when the prompt or the
  distiller changes) re-distils every ticket exactly once. That is how an improvement reaches
  tickets nobody has edited.
- A cached hit whose document no longer exists is dropped and the response is marked
  `stale: true`, so the UI can offer Refresh.
- Attaching a document never changes the ticket's status; a file may be on several tickets.
- `search_terms_fingerprint` is the column added by `0004_ticket_search_terms.sql`. A ticket written
  before that migration simply re-distils once.

### Adding a file from a ticket

The desktop app reuses the Graph Add wizard with the ticket as context:
`POST /api/graph-add/suggestions` now accepts an optional `context` form field (the ticket's title
and description, ≤ 500 characters). The document is still scored on its own words; the context is
scored separately on the same folders and can carry a folder the document does not name, at half
strength — so a confident document match is never overruled. After `POST /placements` succeeds the
app links the new file with `POST /tickets/{id}/files` (`source: "upload"`), which is what writes
the ticket-scoped activity event.

### Activity

`ticket_events` is append-only and feeds the "Changes and updates" panel. Ticket kinds:
`ticket_created`, `ticket_assigned`, `ticket_status_changed`, `ticket_completed`,
`ticket_reopened`, `ticket_updated`, `ticket_commented`, `file_attached`, `file_detached`.
Project kinds (no ticket): `project_shared`, `project_member_removed`, `files_uploaded` (Graph
Creation), `file_added` (Graph Add), `document_saved` (the editor). Sections write through
`app/core/activity.py`, whose default is a no-op so unit tests stay hermetic — a failed audit row
never fails an upload, a save or a placement.

### Trying it without the app

```powershell
# sign in, then use the id it returns as X-Dev-User-Id
curl.exe -X POST http://localhost:8000/api/tickets/members -H "Content-Type: application/json" -d "{\"display_name\":\"Ada\"}"

# a ticket, then its files (the first open runs the search; the second is cached)
curl.exe -X POST http://localhost:8000/api/tickets/tickets -H "Content-Type: application/json" -H "X-Dev-User-Id: <member-id>" -d "{\"project_id\":\"<uuid>\",\"title\":\"Fix the login redirect\"}"
curl.exe "http://localhost:8000/api/tickets/tickets/<ticket-id>" -H "X-Dev-User-Id: <member-id>"
```

Offline (no Supabase, no model calls):

```powershell
..\\.venv\\Scripts\\python.exe -m app.tickets.tools.verify_tickets
..\\.venv\\Scripts\\python.exe -m app.tickets.tools.seed_demo --project-id <uuid>
```

`verify_tickets` is an in-memory walkthrough (identity → sharing → cached search → attach →
complete → feed). `seed_demo` writes a demo to the configured Supabase project: three named
members, a shared project, four tickets, a comment, a completion and two attached documents.

### Rewriting older descriptions as prose

Descriptions written before the plain-prose rule may still contain `rollback-plan` or
`deploy_run`. This tool rewrites them in place — separators become spaces, every word is kept,
code spans and URLs are untouched, and **no model is called**:

```powershell
..\\.venv\\Scripts\\python.exe -m app.graph_creation.tools.normalise_descriptions          # report only
..\\.venv\\Scripts\\python.exe -m app.graph_creation.tools.normalise_descriptions --apply  # write
```

Add `--project-id <uuid>` to sweep one project. A folder's description is not re-described;
only its punctuation changes, so no quota is spent and the tree keeps its shape.

## Chat endpoints

Mounted at `/api/chat`. **A project is its group chat**: there is no channel table and nothing to
create, because `chat_messages.project_id` *is* the channel. Every project therefore already has
one, sharing a project (`project_members`) puts the member in its chat, and deleting the project
takes its messages with it. Access is `ProjectAccess.require`, so a stranger gets `404`.

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/channels` | my projects as chats, newest activity first, each with its last message |
| `GET` | `/projects/{id}/messages?after_seq=&limit=` | the newest page (`seq` ascending), or everything after a cursor |
| `POST` | `/projects/{id}/messages` | `{ "body": "…" }` → the stored message, mentions resolved |
| `DELETE` | `/messages/{id}` | soft delete (body becomes `[deleted]`); the author, or the project owner |
| `GET` | `/projects/{id}/mention-targets?q=` | documents, folders, tickets and calendar events the composer may offer |

**Mentions.** The composer writes a marker into the text — `@[auth.md](file:<uuid>)`,
`@[guides](directory:<uuid>)`, `@[Fix the redirect](ticket:<uuid>)`,
`@[Kickoff](event:<uuid>)` — and the backend parses it, checks every id belongs to *that* project,
and stores the resolved set on the row (`mentions jsonb`: kind, id, label, path, directory path,
ticket number, event day). One source of truth means what a reader sees is what was validated; an
unknown or foreign id is a `400`. The marker grammar itself lives in
[`app/core/mentions.py`](app/core/mentions.py), because an event's notes write the same syntax.
A deleted message keeps its row (and `seq`) so pollers never gap.

**Polling, not sockets.** The desktop renderer has no network access, so it asks
`GET …/messages?after_seq=<last seq>` every ~3 s while the chat is visible (`useChat` pauses while
the window is hidden). Nothing here calls a model, and nothing writes to a project tree.

Pressing a chip is what ties chat to the rest of the app: a document opens the project graph
focused on that file, a folder opens it at that folder, a ticket opens the tickets screen on that
ticket, and an event opens the calendar on the event's day. The reverse direction is a button on
the other screens: a calendar event's **Message in chat** and a ticket's **Discuss in chat** open
the composer with the matching marker already written.

## Calendar endpoints

Mounted at `/api/calendar`. Two calendars share one shape:

* **`GET /personal?from=&to=`** — the individual calendar, merging every project the caller is in:
  their own (personal) events, those projects' events, and **only the deadlines of tickets
  assigned to them**.
* **`GET /projects/{id}?from=&to=`** — a project calendar: its events and **every** ticket
  deadline in it.
* **`POST /events`**, **`PATCH /events/{id}`**, **`DELETE /events/{id}`** — events.
* **`GET /projects/{id}/mention-targets?q=`** — documents, folders and tickets an event's notes
  may mention after an `@`.
* **`GET /projects/{id}/mentioning/{kind}/{target_id}`** — the events whose notes mention one of
  those. This is what a ticket panel reads to show the events a ticket is discussed in.

An event with `project_id` is a **project event** (every project member sees it); without it, a
**personal event** (only its creator sees it). Only the creator may edit or delete an event. A
range is at most 400 days and `ends_at` may not precede `starts_at`.

**Event mentions.** An event's `notes` use the same `@[label](kind:id)` markers as chat. They are
parsed and validated against the event's project when it is written (`_resolve_notes`), and stored
resolved in `calendar_events.mentions` ([migration 0007](../supabase/migrations/0007_calendar_mentions.sql)),
so the calendar can draw chips, chat can resolve an event mention, and a ticket's panel can ask
which events mention it without re-reading every event. A personal event has no project to check a
mention against, so markers there stay plain text. No model is called.

**Deadlines are not copied.** They are read from `tickets.due_date` through
[`app/tickets/public.py`](app/tickets/public.py) on every request, so editing a ticket moves its
deadline immediately, and a `done` ticket stops appearing. Nothing is written to a ticket and no
model is called. Items sit on the day they start.

## Test & lint

```powershell
..\.venv\Scripts\python.exe -m pytest
..\.venv\Scripts\python.exe -m ruff check .
..\.venv\Scripts\python.exe -m ruff format .
```

The suite is hermetic — settings are blanked, auth runs in dev mode, and the section tests
use an in-memory repository, an in-memory object store and each section's mock describer (or,
for search, the real local scorer; for tickets, the offline distiller). Nothing
touches Supabase, a model provider or the network.

## Structure

```text
app/
├─ main.py            # app factory, lifespan, CORS, mounts the section routers
├─ core/config.py     # Settings (pydantic-settings) — the only place env vars are read
├─ core/auth.py       # get_current_user (dev header or Supabase bearer token)
├─ core/access.py     # project membership, shared by every section
├─ core/activity.py   # the write side of the changes-and-updates feed (no-op default)
├─ core/mentions.py   # the `@[label](kind:id)` marker: parse, clean, dedupe (pure; chat + calendar)
├─ db/supabase.py     # admin_client() / anon_client(), reachability ping
├─ health/router.py
├─ core/text.py       # shared vocabulary work: tokens, stems, scoring, excerpts
├─ graph_creation/    # SECTION — implemented
│  ├─ router.py       # HTTP surface
│  ├─ service.py      # orchestration: describe → persist, add-mode merge, reads
│  ├─ tree.py         # validation, pruning, ordering, ltree paths
│  ├─ ingest.py       # multipart / zip parsing and limits
│  ├─ extract.py      # markdown → prompt text
│  ├─ describe.py     # directory descriptions (Gemini + mock)
│  ├─ storage.py      # Supabase Storage, content-addressed keys
│  ├─ repository.py   # PostgREST access (protocol + Supabase implementation)
│  └─ tests/
├─ graph_add/         # SECTION — implemented
│  ├─ router.py       # HTTP surface (suggest → place)
│  ├─ service.py      # orchestration, conflicts, one-call description refresh
│  ├─ navigate.py     # local folder ranking (no model call)
│  ├─ scoring.py      # the document reduced to a compact query
│  ├─ describer.py    # batched description refresh (Gemini + mock)
│  ├─ prompts.py      # the single refresh prompt
│  ├─ labels.py       # folder + file naming, ltree labels, rename suggestions
│  ├─ extract.py      # markdown → prompt text
│  ├─ storage.py      # content-addressed blobs (put + get)
│  ├─ repository.py   # PostgREST access (add_requests + tree writes)
│  └─ tests/
└─ graph_ai_search/   # SECTION — implemented (local search: descriptions + document text)
   ├─ search.py       # the walk: score folders, read documents, rank
   ├─ scoring.py      # folder/document scoring (weights shared with Graph Add)
   ├─ storage.py      # reads document bodies, digest-keyed LRU
   ├─ public.py       # the only module another section may import (build + search)
   ├─ router.py, service.py, schemas.py, repository.py
   └─ tests/
└─ tickets/           # SECTION — implemented (names, sharing, tickets, cached files, feed)
   ├─ router.py       # HTTP surface
   ├─ service.py      # identity, sharing, tickets, completion, comments, the cache
   ├─ repository.py   # PostgREST access (members, tickets, files, events)
   ├─ schemas.py      # request/response models
   ├─ cache.py        # the two fingerprints (terms + results) and the no-model fallback query
   ├─ distill.py      # one model call: a ticket's wording → its search terms (or the offline one)
   ├─ adapters.py     # Graph AI Search through its public module
   ├─ tools/          # verify_tickets (offline), seed_demo (Supabase)
   └─ tests/
├─ chat/              # SECTION — implemented (one group chat per project, with mentions)
│  ├─ router.py       # HTTP surface
│  ├─ service.py      # membership, message resolution, channels
│  ├─ mentions.py     # the chat's import site for app.core.mentions (the marker grammar)
│  ├─ adapters.py     # mention targets through the graph + tickets + calendar public modules
│  ├─ repository.py   # PostgREST access (chat_messages, names)
│  ├─ schemas.py
│  └─ tests/
└─ calendar/          # SECTION — implemented (project calendars + the merged individual one)
   ├─ router.py       # HTTP surface
   ├─ service.py      # scope rules, event ownership, event mentions, deadline merge
   ├─ adapters.py     # deadlines + mention targets through the other sections' public modules
   ├─ public.py       # the only module another section may import (events as mention targets)
   ├─ repository.py   # PostgREST access (calendar_events, names)
   ├─ schemas.py
   └─ tests/
```

## Configuration

All settings and defaults live in `app/core/config.py`; env var names are in
`.env.example`. Read them with `get_settings()` — never `os.environ` in section code.

| Variable | Notes |
| --- | --- |
| `APP_ENV`, `LOG_LEVEL`, `API_PREFIX` | Operational defaults |
| `CORS_ORIGINS` | Comma separated (or JSON list); add the Electron origin later |
| `AUTH_MODE`, `DEV_USER_ID` | `dev` trusts `X-Dev-User-Id`; `supabase` verifies the bearer token. The id is a `members.id` after migration 0003 — `POST /api/tickets/members` creates one from a name |
| `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY` | Service role bypasses RLS — server-side only |
| `STORAGE_BUCKET` | Bucket for uploaded markdown (default `project-files`) |
| `GEMINI_API_KEY`, `GEMINI_MODEL`, `GEMINI_THINKING_LEVEL`, `GEMINI_FALLBACK_MODELS` | The only describer provider (`google-genai`). Default model `gemini-3.1-flash-lite`; 2.5 models are access-gated and answer `404 model not found` for newer projects. Fallbacks are empty by default, so every description comes from that model. `GEMINI_THINKING_LEVEL` is `minimal` / `low` / `medium` / `high`; blank (the default) sends no thinking config at all, which is cheapest. There is no numeric thinking budget: models from 3.5 onwards reject it |
| `SUMMARIZER`, `SUMMARY_MAX_INPUT_CHARS`, `SUMMARY_CONCURRENCY` | `gemini` / `mock`; the offline mock is used when no key is configured (and by the tests); the character cap when a document is read for a prompt; how many folder descriptions run at once (4 by default) |
| `DESCRIPTION_FILE_HEAD_CHARS`, `DESCRIPTION_MAX_INPUT_CHARS`, `DESCRIPTION_MAX_CHARS` | How much of each file (1500) and of one folder (24000) reaches a description prompt, and the hard ceiling (300 characters) for the description that comes back |
| `FILE_EDIT_MAX_CHARS` | Characters of one document the app loads for editing (400 000). Longer documents open truncated and read-only; a save is still capped by `MAX_FILE_BYTES` |
| `LLM_MIN_INTERVAL_SECONDS` | Minimum gap between the starts of model calls (2 s). Retries and fallback models are paced too |
| `SCORING_FOLDER_THRESHOLD` | Share of a query a folder description must cover before a **search** opens that branch (0.25) |
| `SEARCH_MAX_FILES_READ`, `SEARCH_MAX_DOCUMENT_CHARS`, `BLOB_CACHE_ENTRIES` | Search's read budget (200 documents), per-document cap (200k characters) and digest cache size (256) |
| `MAX_UPLOAD_FILES`, `MAX_UPLOAD_BYTES`, `MAX_FILE_BYTES`, `MAX_DIRECTORY_DEPTH` | Upload limits |

## Known limitations

- **Chat is polled, not pushed.** A message can take up to ~3 seconds to appear for somebody else
  (a 3-second poll in `useChat`). There is no typing indicator, read receipt, reaction, thread or
  message edit; deletion is a soft delete (`[deleted]`) so the `seq` cursor never gaps.
- **A calendar item sits on the day it starts.** A multi-day event is drawn on its first day, not
  repeated across the range. An all-day event is stored at UTC midnight so its day is stable in
  every timezone; a timed event keeps the machine's offset.
- **Deadlines are read live and are never editable from the calendar.** Changing one means editing
  the ticket; a `done` ticket's deadline drops off the calendar.

- **Identity is a name, and that is the whole check.** `X-Dev-User-Id` is trusted in
  `AUTH_MODE=dev`, and a member is created by typing a name on the startup screen. Anyone can be
  anyone: this is a hackathon build, not a security model. `AUTH_MODE=supabase` still verifies
  bearer tokens, but members and auth users are no longer the same thing.

- **Background jobs are in-process `asyncio` tasks.** Run a single uvicorn worker; a hard
  crash mid-job leaves that job row unfinished (no partial tree is ever written, because
  every description is produced before anything is inserted). A real job queue is the next
  step if we need durability.
- **Blob writes are retried twice** on a transient transport error, because a dropped socket
  must not discard a job whose descriptions are already paid for (Windows raises
  `WinError 10035` under concurrent uploads). For the same reason the shared Supabase client
  runs over **HTTP/1.1**: storage3 builds its own client with `http2=True`, and httpcore's
  sync HTTP/2 read is the call that fails. Uploads still run 4 at a time.
- **The service-role client bypasses RLS,** so ownership is enforced in
  `GraphCreationService` (`_require_project`, `get_job`). The RLS policies in the
  migration protect direct access from the Electron app with a user JWT.
- **`ltree` paths are derived, not authoritative.** The human-readable `path` column is
  what the API returns and what uniqueness is enforced on; `ltree_path` exists for
  subtree queries (`where ltree_path <@ 'docs.api'`).
