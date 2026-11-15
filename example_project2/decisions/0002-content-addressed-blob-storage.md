# ADR 0002: Content-Addressed Blob Storage

- **Status:** accepted
- **Date:** 2026-04-18
- **Deciders:** platform team
- **Related:** [Ingestion pipeline](../architecture/ingestion-pipeline.md)

## Context

Documentation sets are re-imported often, and large organisations import the same files into
several projects. The prototype stored blobs under `projects/{id}/{path}`, so:

- Re-importing an unchanged folder rewrote every object.
- The same file in two projects was stored twice.
- Every re-import changed every storage key, breaking cached download URLs.

## Decision

Address blobs by the SHA-256 of their normalised bytes:

```text
blobs/{hash[0:2]}/{hash}/{filename}
```

`files.content_hash` stores the digest; the database, not the path, carries the association
between a tree position and a blob.

## Consequences

**Good**

- Re-importing an unchanged file is a no-op — same hash, same object.
- Duplicates across projects cost one object.
- A download URL stays valid across imports as long as content is unchanged.
- Deletion becomes a reference-count question rather than a path question.

**Bad**

- Deletion needs care: a blob may be referenced by several projects, so we cannot delete by key
  on project removal. The delete path counts references first, inside the same transaction.
- Per-tenant key prefixes no longer exist, so storage-level isolation is weaker; the API is now
  the only place tenant scoping is enforced for blobs.
- Hash collisions are theoretically possible. We accept this for markdown; SHA-256 collisions
  are not a practical concern at our scale.

**Neutral**

- A blob that loses its last reference is deleted lazily by a nightly sweep, so orphaned bytes
  are possible for up to 24 hours.

## Alternatives Considered

| Alternative | Why rejected |
| :--- | :--- |
| Path-based keys with ETag dedupe | ETags differ by server; not portable across stores |
| Dedupe by size and name | Cheap but wrong the moment a file is edited |
| Keep duplicates per project | Simplest, but storage cost grows linearly with re-imports |

## Follow-Up

The reference count is computed, not stored, to avoid drift. If the nightly sweep becomes slow,
add a `blob_refs` table and maintain it in the same transaction as `files`.
