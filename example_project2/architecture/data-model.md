# Data Model

Five tables hold everything Meridian knows about a tree. Document bodies never go in Postgres —
only their summaries and a pointer into object storage.

## Entity Relationships

```text
projects ──1:N──▶ directories ──1:N──▶ files
    │                  │  ▲
    │                  └──┘ self-reference (parent_id) + ltree path
    ├──1:N──▶ import_jobs
    └──1:N──▶ add_requests
```

## Tables

| Table | Purpose | Notes |
| :--- | :--- | :--- |
| `projects` | One documentation set | Holds name, owner, document count |
| `directories` | Every folder, root included | `path` is `ltree`, `parent_id` is self-referencing |
| `files` | Every document | `content_hash` points at the blob, `summary` is text |
| `import_jobs` | Import progress | `stage`, `processed_nodes`, `error` |
| `add_requests` | A pending placement suggestion | Expires after 24 hours, single use |

## The `directories` Path

`path` mirrors the folder's position using `ltree`, so a whole subtree is one predicate:

```sql
SELECT name, description, file_count
FROM directories
WHERE project_id = $1
  AND path <@ 'operations.runbooks'::ltree;
```

Ordering by `path` gives a stable depth-first traversal without recursion. Indexes are on
`(project_id, path)` and a GIST index on `path` for subtree lookups. The choice is recorded in
[ADR 0001](../decisions/0001-use-postgres-ltree.md).

## Invariants

1. Every directory has exactly one parent, except the project root.
2. A directory's `file_count` counts only files it holds directly, not descendants.
3. Every described directory's `description` mentions each child folder exactly once.
4. A file's `content_hash` is the SHA-256 of its normalised bytes; equal hashes share a blob.
5. `add_requests` rows are never reused — placement consumes them.

## Status Columns

| Column | Values |
| :--- | :--- |
| `files.summary_status` | `pending`, `done`, `skipped`, `failed` |
| `directories.description_status` | `pending`, `done`, `stale`, `failed` |
| `import_jobs.status` | `queued`, `running`, `succeeded`, `failed`, `cancelled` |

`stale` is set when a descendant changes, which is what triggers the re-description described
in [Placing a new document](../tutorials/placing-a-new-document.md).

## Migrations

Schema changes live in `deploy/migrations` and are applied forward only. Worst-case rollback is
a redeploy of the previous image, which is always schema-compatible for one minor version — see
[Release process](../contributing/release-process.md).
