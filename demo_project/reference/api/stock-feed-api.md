# Stock Feed API

Status: Draft · Owner: Dan Whitcombe · Last updated: 2026-11-13

How a warehouse or store system submits a batch to the ingestor, and what it gets back. Every source
uses this endpoint, whether it pushes or is polled into it.

## Base

```text
https://feeds.harbourandheath.internal/v1
```

## `POST /batch`

```http
POST /v1/batch
Authorization: Bearer <token>
X-Feed-Signature: sha256=<hmac>
X-Feed-Timestamp: 2026-11-13T09:41:00Z
Content-Type: application/json
```

Body is the [feed message](../data-dictionary/feed-message.md) envelope.

| Response | Meaning | Source action |
| :--- | :--- | :--- |
| 202 | Accepted, queued | Advance cursor |
| 400 | Malformed envelope | Do not retry; alert |
| 401 | Bad token or signature | Refresh credential |
| 403 | Not permitted for that location | Configuration error |
| 409 | Cursor mismatch, snapshot requested | Wait for snapshot |
| 413 | Batch too large | Split the batch |
| 422 | Validation failed | Do not retry; alert |

A `409` is the only response that asks the source to do something different rather than to retry. The
ingestor follows it immediately with a snapshot request.

## `POST /snapshot`

A snapshot is the same envelope with `shape: "snapshot"` and no cursor fields. Snapshots are accepted
outside the normal cadence and always replace, never merge.

| Rule | Detail |
| :--- | :--- |
| Maximum records | 250,000 |
| Maximum size | 200 MB |
| Required | `record_count` matching the rows |
| Accepted during maintenance | Yes, if the source can produce one |

## `GET /batch/{batch_id}`

Status of a submitted batch, for a source that wants to confirm before advancing its cursor.

```json
{ "batch_id": "ng-20261113-0941", "status": "applied",
  "records": 2410, "applied": 2398, "quarantined": 12,
  "received_at": "2026-11-13T09:41:04Z", "applied_at": "2026-11-13T09:41:08Z" }
```

| Status | Meaning |
| :--- | :--- |
| `received` | Queued |
| `validating` | Pre-flight checks |
| `applied` | Written and published |
| `rejected` | Failed validation; see `reason` |
| `superseded` | A snapshot replaced it before it applied |

## `GET /health`

Per-source freshness, for warehouse dashboards and our own monitoring.

```json
{ "sources": [ { "source": "northgate", "last_good": "2026-11-13T09:41:00Z",
                 "stale": false, "threshold_seconds": 1200, "missed_cycles": 0 } ] }
```

## Idempotency

`(source, batch_id)` is the idempotency key. A repeated submission returns `202` and is discarded, never
rejected, so a source that retries after a network timeout can safely advance its cursor.

## Polling

For sources that cannot push, the ingestor polls on the cadence in
[polling and cadence](../../stock-feeds/protocol/polling-and-cadence.md). The source exposes either a
paginated list endpoint or a database view; the ingestor adapts, the contract does not change.

## Related

[Feed contracts](../../stock-feeds/protocol/feed-contracts.md) ·
[Authentication](../../stock-feeds/protocol/authentication.md) ·
[Error codes](./error-codes.md)
