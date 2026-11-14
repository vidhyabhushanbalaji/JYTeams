# Search

One read-only endpoint answers questions about a project's tree.

## `POST /api/search`

```json
{
  "project_id": "prj_91c2",
  "query": "what should I do if the primary database fails?",
  "limit": 10
}
```

| Field | Type | Notes |
| :--- | :--- | :--- |
| `project_id` | string | Required |
| `query` | string | 2–2 000 characters |
| `limit` | integer | 1–100, default 25 |
| `max_folders` | integer | Optional cap; setting it disables the fallback sweep |

## Response

```json
{
  "query": "what should I do if the primary database fails?",
  "results": [
    {
      "file_id": "fil_71b0",
      "path": "operations/runbooks/database-failover.md",
      "summary": "Promoting the Postgres replica after primary loss.",
      "relevance": 0.94
    },
    {
      "file_id": "fil_6a18",
      "path": "architecture/deployment-topology.md",
      "summary": "Services, scaling signals and failure behaviour.",
      "relevance": 0.61
    }
  ],
  "folders_visited": 9,
  "fallback_used": false,
  "duration_ms": 3412
}
```

Results are ordered by `relevance` from a single ranking call, so scores within one response are
comparable. Do not compare scores across responses.

## Reading the Metadata

`folders_visited` is the honest cost signal — it drives billing and the `search.slow` event.
`fallback_used: true` means nothing matched on the first pass and a full sweep ran, which usually
means the query used vocabulary the documentation does not.

## Empty Results

An empty `results` array with `fallback_used: true` is a real "not found". An empty array with
`fallback_used: false` and a low `folders_visited` can indicate an over-cautious branch
description; rephrase with words the docs use, or omit `max_folders`.

## What Search Does Not Do

- It does not read file bodies — only summaries and descriptions.
- It does not search across projects; pass one `project_id`.
- It does not write anything, so it is safe to call in a read-only dashboard.

## Performance

Typical latency is 1.5–4 s for trees under 100 folders. Trees above 300 folders should set
`max_folders` and accept a narrower answer. See
[Search service](../../architecture/services/search-service.md) and the
[SLOs](../../operations/service-level-objectives.md).
