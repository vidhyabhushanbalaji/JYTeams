# Glossary

Every Meridian-specific term in one place. Alphabetical.

## A–C

**Add request** — A pending placement suggestion. Holds candidate folders, expires after 24
hours, and can be committed once. Stored in `add_requests`.

**Ancestor re-description** — After a file is written, its parent folder and all ancestors are
re-described bottom-up so descriptions stay accurate. See
[Placing a new document](../tutorials/placing-a-new-document.md).

**Audit row** — An append-only record of a mutating action: actor, action, target, request id.
Retained 400 days.

**Blob** — The stored bytes of one document, addressed by the SHA-256 of its content. Identical
files share one blob.

**Candidate** — A folder offered as a placement destination. Always includes the project root.

**Consolidation call** — The single model call that ranks candidates (placement) or files
(search). It exists because relevance scores from separate calls are not comparable.

**Content hash** — SHA-256 of a document's normalised bytes. The primary key of a blob.

## D–H

**Description** — The prose attached to a folder, generated from its child folder descriptions
and child file summaries. Distinct from a file's *summary*.

**Directory** — A folder in the tree, including the root. Has exactly one parent, except the
root. Stored in `directories`.

**Document count** — The number of files a folder holds **directly**, not including
descendants. Used for the fallback-sweep threshold.

**Fallback sweep** — A full traversal of every folder, run when a search logs nothing and the
project has at most 40 documents. Disabled when `MERIDIAN_SEARCH_MAX_FOLDERS` is set.

**Frontier** — The set of folders a search walk has queued but not yet visited. The walk ends
when the frontier is empty.

## I–L

**Import job** — A single import run. Tracks `stage`, `processed_nodes` and errors. One at a
time per project.

**Leaf** — A directory with no child directories. May still hold files. Placement candidates
are usually leaves.

**Lease** — A time-limited claim a worker holds on a job. Expires after five minutes of silence
so a crashed worker does not block the queue.

**`ltree`** — Postgres extension storing a dot-separated path with containment operators. Powers
subtree queries. See [ADR 0001](../decisions/0001-use-postgres-ltree.md).

## M–R

**Placement** — Choosing a folder for one new document, then committing it. Two steps: suggest,
then commit.

**Pruning** — Dropping empty directories, or in search, skipping a branch because its description
does not align with the query.

**Project** — A container for one documentation tree. All resources are scoped to a project.

**Prompt injection** — Text inside a document that attempts to alter model behaviour. Mitigated
by having no tools and validating output shape; see
[Threat model](../security/threat-model.md).

**Root** — The project's top-level directory. Always a placement candidate.

## S–Z

**Skipped** — A file stored without a summary because it is not markdown or too large. It is
listed but never searchable.

**Stage** — One of the seven import phases, from receive to describe folders.

**Stale** — A folder description that a descendant change invalidated. Set before re-description
so a crash mid-way is visible.

**Summary** — The 1–2 sentence description of one file. The only thing search reads besides
folder descriptions.

**Tenant** — The isolation unit. Users, tokens and projects belong to exactly one tenant.

**Walk** — The search traversal: one model call per visited folder, expanding into relevant
subfolders. See [Search service](../architecture/services/search-service.md).
