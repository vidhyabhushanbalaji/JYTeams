# Backend Section Ownership — Scoped Writes

The backend is split into three independent sections. Each is a Python package under
`backend/app/`. **All three are implemented** and were designed with the team before they were
written; anything new still gets agreed first, one section at a time.

| Section | Directory | HTTP prefix | State |
| --- | --- | --- | --- |
| Graph Creation | `backend/app/graph_creation/` | `/api/graph-creation` | implemented |
| Graph Add | `backend/app/graph_add/` | `/api/graph-add` | implemented |
| Graph AI Search | `backend/app/graph_ai_search/` | `/api/graph-ai-search` | implemented |

**Shared foundation (no single owner):** `backend/app/main.py`,
`backend/app/core/`, `backend/app/db/`, `backend/app/health/`, `backend/tests/`,
`backend/requirements*.txt`, `backend/pyproject.toml`, `backend/.env*`,
`backend/README.md`, `supabase/migrations/`, `frontend/`, `.clinerules/`,
root `README.md` and `.gitignore`.

## Rules

1. State which section you are working in at the start of the task. Work in **exactly
   one** section per task.
2. **Read anything. Write only inside your section** — including that section's own
   `tests/` directory.
3. **Ask for permission before you:**
   - write or edit any file outside your section, including shared foundation files;
   - touch another section at all;
   - add, remove or change a dependency (`requirements*.txt`, `pyproject.toml`);
   - change configuration, env files or driver/client wiring;
   - run anything that mutates data or schema (constraints, indexes, `MERGE`,
     `DELETE`, `DROP`, migrations, data imports against a real database);
   - delete or rename a file you did not create in this task.
4. Permission requests must be one short message: files affected → why → risk → what
   you intend to change. Then **stop and wait** for an answer.
5. **Exemptions.** If the user explicitly says so — e.g. "cross-section is fine",
   "scope: all", "ignore the section rule" — or names the exact files, the rule is
   lifted **for that one task only**. It does not carry over to the next task. If a
   message is ambiguous, treat it as **not approved** and ask.
6. If your section genuinely needs shared code, do not silently edit shared files.
   Either keep the helper inside your section, or ask as described above.
7. Never import another section's internals (repositories, services, helpers). If you
   need something from another section, ask for an agreed interface first.
8. Finish a task by reporting: files changed (grouped by section vs. shared), any
   approved cross-scope change, and the test command you ran.
