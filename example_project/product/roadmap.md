# Roadmap

Plans are directional, not commitments. Anything at `Now` has an owner and an issue; anything at
`Later` does not.

## Now (current quarter)

| Item | Why | Status |
| :--- | :--- | :--- |
| Incremental re-import | Re-importing 400 files to change one is wasteful | In progress |
| Search result excerpts | Users want two lines of context, not just a summary | In progress |
| Placement explanation polish | Reasons are terse; they should read like a colleague | In progress |

## Next (next quarter)

| Item | Why |
| :--- | :--- |
| Folder-level permissions | Enterprise tenants ask for it in every review |
| Multimodal import | Diagrams and PDFs are the most common skipped files |
| Saved searches and alerts | Teams want to be told when new docs match a topic |
| Bulk placement | Adding a folder of new documents one at a time is tedious |

## Later (no date)

- Self-hosted model option, to remove the provider-retention trade-off in
  [Data privacy](../security/data-privacy.md).
- Cross-project search with explicit project selection.
- Version history for documents, which implies content addressing by revision.
- A public read-only API for embedded search widgets.

## Explicitly Not Planned

| Idea | Why not |
| :--- | :--- |
| Real-time collaborative editing | Meridian is a knowledge index, not an editor |
| Vector database for search | The tree walk is the differentiator; see [ADR 0003](../decisions/0003-single-call-tree-walk.md) |
| Per-file permissions | Folder granularity covers the real request; file-level is unmanageable |
| Automatic document merging | Too destructive to automate; a suggestion tool at most |

## How Items Get Promoted

An item moves from `Later` to `Next` when it has: a named owner, a rough cost estimate, and at
least three tenants asking for it — or one tenant paying for it. Everything else stays a note.

## Recently Shipped

- Project deletion with shared-blob retention (`1.8`)
- Webhook signature rotation with a 24-hour overlap (`1.7`)
- Search fallback sweep for small projects (`1.6`)
