# Indexing Service

The indexing service (the worker) does the two jobs that need a model: describing a tree and
placing a document into one. Both are deterministic given the same tree and summaries.

## Job Types

| Job | Trigger | Duration (60 files) |
| :--- | :--- | :--- |
| `import` | `POST /api/projects/:id/import` | 90–150 s |
| `place` | `POST /api/add-requests` | 10–25 s |
| `reindex` | `meridian reindex` | 5–90 s, depending on scope |

## Placement Walk

Placement walks the tree from the root with the incoming document's summary:

1. Call the model once per visited folder, asking which children align with the summary.
2. Only aligned children are opened; unaligned siblings are pruned with their whole subtree.
3. Stop at leaves, at folders where nothing aligns, or when the step budget is exhausted.
4. Collect the stop points as candidates, always including the project root.
5. Run one consolidation call to rank the candidates and produce a reason per candidate.

The consolidation call matters: relevance values from separate calls are not comparable, so
ranking happens once, over the full candidate list.

## Re-Description

After a file is written, the affected folder and its ancestors are re-described bottom-up and
their counts refreshed. Only nodes whose content actually changed are recomputed; ancestors are
marked `stale` first so a crash mid-way is visible and retryable.

## Concurrency

Each worker leases one job at a time from `import_jobs` using `SELECT ... FOR UPDATE SKIP
LOCKED`. `MERIDIAN_SUMMARY_CONCURRENCY` only controls parallel model calls *inside* a job, so
raising it increases cost without changing safety.

## Retries and Idempotency

| Failure | Behaviour |
| :--- | :--- |
| Model timeout | Retried up to `MERIDIAN_RETRY_ATTEMPTS`, then node marked `failed` |
| Rate limit | Exponential backoff with jitter, honours `Retry-After` |
| Worker crash | Job lease expires after 5 min, another worker resumes from the last stage |
| Duplicate upload | Identical `content_hash` reuses the blob; no second summary |

## Observability

Every job emits `meridian_job_duration_seconds`, `meridian_model_calls_total` and
`meridian_job_failures_total`. Dashboards and alert thresholds are documented in
[Monitoring](../../operations/monitoring.md).
