# Failure and Retry

Status: Agreed · Owner: Nadia Kerr · Last updated: 2026-11-06

What the ingestor does when a poll fails, when a batch is wrong, and when it cannot decide. The
principle is that a failure must be either retried or visible, never absorbed.

## Failure taxonomy

| Class | Example | Retry? | Side effects |
| :--- | :--- | :--- | :--- |
| Transport | Timeout, connection reset | Yes, 2 attempts | None |
| Authentication | 401, expired token | Once, after refresh | None |
| Rate limit | 429 | Yes, honouring `Retry-After` | None |
| Server error | 500, 502, 503 | Yes, backoff | None |
| Schema | Missing field, wrong type | No | Batch rejected, alert |
| Cursor mismatch | Unknown starting point | No | Full snapshot requested |
| Completeness | Truncated snapshot | No | Batch rejected, alert |
| Content | Unknown SKU in the batch | Partial | Row quarantined, rest applied |

The last row is the only one where part of a batch is applied. An unknown SKU is a mapping problem,
not a data-integrity problem, and rejecting a whole 210,000-row snapshot because one SKU is new would
stop the warehouse from being sellable.

## Retry policy

| Attempt | Delay | Cumulative |
| :--- | :--- | :--- |
| 1 | Immediate | 0 s |
| 2 | 2 s | 2 s |
| 3 | 8 s | 10 s |

Three attempts fit inside one 15-minute cycle and inside a 5-minute cycle with room to spare. After
three failures the cycle is recorded as missed and the staleness clock starts running, which is the
intended behaviour: retrying harder delays the moment we admit we are stale.

## Where failures go

| Destination | Contents | Alert |
| :--- | :--- | :--- |
| `feed.rejected` table | Whole batches with a reason | Slack, immediate |
| `feed.quarantine` table | Individual rows with a reason | Daily digest |
| `stock.dlq` topic | Events that could not be published | Page after 5 in 10 minutes |
| Ingestor metrics | Cycle counts, latencies, gaps | Dashboard |

The distinction between rejected batches and quarantined rows matters in an incident: a rejected
batch means a warehouse is going stale, a quarantined row means one SKU is missing from the figure.

## Alerting thresholds

| Condition | Severity | Who |
| :--- | :--- | :--- |
| One missed cycle | None | — |
| Two missed cycles | Warning | Platform channel |
| Three missed cycles (source excluded) | High | On-call engineer |
| Cursor mismatch | Medium | Dan Whitcombe, platform channel |
| Snapshot completeness failure | High | On-call engineer |
| More than 50 quarantined rows in a cycle | Medium | Dan Whitcombe |
| Dead-letter events | Medium/High | On-call engineer |

Every alert links to the relevant section of the
[stock feed failure runbook](../../launch-readiness/runbooks/stock-feed-failure.md), because an alert
that requires someone to work out what to do at 03:00 is only half an alert.

## Idempotency

Each batch is keyed by `(source, batch_id)`. A duplicate batch is accepted and discarded with a log
line, not rejected, because a 200 response tells the source it can advance its cursor. Rejecting a
duplicate causes the source to retry forever, which is how a small glitch becomes an outage.

## What is not retried

A schema failure is never retried automatically. A source that starts sending a string where an
integer should be will do so consistently, and retrying turns one alert into a hundred. The batch is
rejected, the source goes stale, and a human is paged.

## Related

[Stale stock handling](./stale-stock-handling.md) · [Feed incidents](./feed-incidents.md) ·
[Integration landscape](../../current-state/systems/integration-landscape.md)
