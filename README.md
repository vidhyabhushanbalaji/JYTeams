# JYTeams

An Electron desktop app that makes Microsoft Teams **project information easier to
reach**. By Charlie and Bhushan.

Stack: Electron (frontend, later) · Python 3.14 + FastAPI (backend) · Supabase (auth,
Postgres tree, file storage) · Gemini `gemini-3.1-flash-lite` (folder descriptions only, the
only model provider). Neo4j was retired — the project tree is a hierarchy, and `ltree` in
Postgres covers it.

## Status

**Backend and desktop app.** The API boots, health probes work, and **all four sections are
implemented**: upload a directory of markdown files and you get a described tree (one
description per folder, produced bottom-up; documents are stored, never summarised); add a
single document and the service scores every folder locally to suggest where it belongs, then
places it in the folder you choose; search a project for the document that answers a question,
matching locally against folder descriptions and document text; and double-click a document to
read its markdown in the app and save an edit back. **Tickets** sit on top: sign in with a name
(no password — this is a hackathon build), share a project with teammates, keep a personal
to-do list of tasks, and press a ticket to see the project documents it is about — the search
runs once and is cached on the ticket. Details for each:
[`backend/README.md`](backend/README.md).

| Section | Directory | HTTP prefix | State |
| --- | --- | --- | --- |
| Graph Creation | `backend/app/graph_creation/` | `/api/graph-creation` | implemented |
| Graph Add | `backend/app/graph_add/` | `/api/graph-add` | implemented |
| Graph AI Search | `backend/app/graph_ai_search/` | `/api/graph-ai-search` | implemented |
| Tickets | `backend/app/tickets/` | `/api/tickets` | implemented |

The desktop app (`frontend/`) has a rail with **Projects**, **Tickets**, the API/DB status and
**Settings**, plus the identity chip that switches user.

## Quickstart (backend)

```powershell
# 1. dependencies — into the repo-root virtualenv (Python 3.14)
.\.venv\Scripts\python.exe -m pip install -r backend\requirements-dev.txt

# 2. configuration
Copy-Item backend\.env.example backend\.env   # then fill in Supabase / Gemini

# 3. database schema — paste supabase\migrations\0001_graph_creation.sql,
#    0002_graph_add.sql and 0003_tickets.sql into the Supabase SQL editor (or
#    `npx supabase db push`), then create a private `project-files` storage bucket.
#    0003 makes `members` the identity (a name, no password) and adds tickets.

# 4. run
cd backend
..\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000   # port taken? use --port 8001
```

- API docs: <http://localhost:8000/docs>
- Health: <http://localhost:8000/health>, `/health/supabase`
- Add one document: `..\.venv\Scripts\python.exe -m app.graph_add.tools.add_file ..\notes\auth.md --project-id <uuid>`

More detail, including tests and credentials setup: [`backend/README.md`](backend/README.md).

## Repository layout

```text
.clinerules/          # agent rules — section ownership is enforced here
.cline/skills/        # workspace agent skills (find-skills)
backend/              # FastAPI service (app/, tests/, requirements*.txt, .env.example)
supabase/migrations/   # SQL schema (projects, directories, files, creation_jobs, add_requests,
                       #             members, project_members, tickets, ticket_files,
                       #             ticket_comments, ticket_events)
frontend/             # Electron app (Projects + Tickets, React)
```

## Working together

`.clinerules/10-backend-section-ownership.md` defines the write-scope rule: an agent (or
person) works in **one** section at a time, may read anything, and must ask before
touching shared code, another section, dependencies or configuration.
