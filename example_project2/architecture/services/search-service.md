# Search Service

Search is read-only and stateless: it reads the stored summaries and descriptions, walks the
tree, and returns ranked files. It never writes to a project.

## The Walk

One model call per folder answers two questions at once:

1. Which files *in this folder* answer the query?
2. Which subfolders *could* contain an answer?

Every matching file is logged, and every matching subfolder is opened. There is no expansion
budget by default, so the walk ends when the frontier is empty and cost follows how much of the
tree the model considers relevant.

## Fallback Sweep

If nothing was logged and the project holds at most `MERIDIAN_SEARCH_FALLBACK_LIMIT` documents
(40 by default), every folder is swept once. This exists because a vague folder description can
otherwise hide a whole branch. Setting `MERIDIAN_SEARCH_MAX_FOLDERS` disables the fallback —
the cap is a valve, not a tuning knob.

## Ranking

Logged files are ranked in one consolidation call, batched by `MERIDIAN_SEARCH_RANK_BATCH` when
the log is large. Batching is why each batch is ranked with the same rubric text: scores from
separate calls are not comparable without it.

Response shape:

```json
{
  "results": [
    {
      "path": "operations/runbooks/database-failover.md",
      "title": "Database failover",
      "summary": "Step-by-step promotion of the Postgres replica...",
      "relevance": 0.93
    }
  ],
  "folders_visited": 7,
  "fallback_used": false
}
```

## Limits

| Limit | Value | Source |
| :--- | :--- | :--- |
| Query length | 2 000 chars | Request validation |
| Folders visited | unlimited | Unless `MERIDIAN_SEARCH_MAX_FOLDERS` is set |
| Results returned | 25 | `limit` parameter, max 100 |
| Concurrent searches per tenant | 4 | Rate limits |

## Known Weakness

A query whose wording appears in no summary cannot be found, because search never reads file
bodies. Phrase queries in the vocabulary the documentation already uses, or raise the fallback
limit. This trade-off is deliberate — see
[ADR 0003](../../decisions/0003-single-call-tree-walk.md).

## Related
- [Search endpoint](../../api/endpoints/search.md)
- [Service level objectives](../../operations/service-level-objectives.md)
