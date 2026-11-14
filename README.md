# JYTeams

An Electron desktop app that makes Microsoft Teams **project information easier to
reach**. By Charlie and Bhushan.

Stack: Electron (frontend, later) · Python 3.14 + FastAPI (backend) · Supabase (auth,
Postgres tree, file storage) · Gemini (summaries). Neo4j was retired — the project tree is
a hierarchy, and `ltree` in Postgres covers it.

## Status

**Backend only.** The API boots, health probes work, and **Graph Creation is
implemented**: upload a directory of markdown files and you get a described tree
(per-file summaries, per-directory descriptions produced bottom-up). Graph Add and
Graph AI Search are still empty scaffolds, designed one section at a time.

| Section | Directory | HTTP prefix | State |
| --- | --- | --- | --- |
| Graph Creation | `backend/app/graph_creation/` | `/api/graph-creation` | implemented |
| Graph Add | `backend/app/graph_add/` | `/api/graph-add` | scaffold |
| Graph AI Search | `backend/app/graph_ai_search/` | `/api/graph-ai-search` | scaffold |

## Quickstart (backend)

```powershell
# 1. dependencies — into the repo-root virtualenv (Python 3.14)
.\.venv\Scripts\python.exe -m pip install -r backend\requirements-dev.txt

# 2. configuration
Copy-Item backend\.env.example backend\.env   # then fill in Supabase / Gemini

# 3. database schema — paste supabase\migrations\0001_graph_creation.sql into the
#    Supabase SQL editor (or `npx supabase db push`), then create a private
#    `project-files` storage bucket.

# 4. run
cd backend
..\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```

- API docs: <http://localhost:8000/docs>
- Health: <http://localhost:8000/health>, `/health/neo4j`, `/health/supabase`

More detail, including tests and credentials setup: [`backend/README.md`](backend/README.md).

## Repository layout

```text
.clinerules/          # agent rules — section ownership is enforced here
.cline/skills/        # workspace agent skills (find-skills)
backend/              # FastAPI service (app/, tests/, requirements*.txt, .env.example)
supabase/migrations/   # SQL schema (projects, directories, files, creation_jobs)
frontend/             # Electron app — placeholder until the backend is done
```

## Working together

`.clinerules/10-backend-section-ownership.md` defines the write-scope rule: an agent (or
person) works in **one** section at a time, may read anything, and must ask before
touching shared code, another section, dependencies or configuration.
