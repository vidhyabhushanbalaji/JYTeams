# Stock Feed Ingestor

Status: Draft · Owner: Nadia Kerr · Last updated: 2026-11-13

Polls five stock sources, validates what they send, computes availability once, and publishes only what
changed. It is the component that decides whether the platform's number is trustworthy.

## Pipeline

```text
poll → authenticate → parse → validate → normalise → join SKUs → compute → publish
```

| Stage | Failure handling |
| :--- | :--- |
| Poll | Retry twice, then record a missed cycle |
| Authenticate | Refresh token once, then alert |
| Parse | Reject the batch, alert |
| Validate | Reject the batch or quarantine rows |
| Normalise | Unknown location rejects the batch |
| Join SKUs | Unknown SKU quarantines the row |
| Compute | Fail the batch rather than publish partial |
| Publish | At-least-once, idempotent by event ID |

## Validation rules

| Rule | On failure |
| :--- | :--- |
| Required fields present | Reject batch |
| Types correct | Reject batch |
| Cursor matches stored cursor | Request full snapshot |
| Row count within 5 % of previous | Reject batch (truncation) |
| Top 500 SKUs present | Reject batch |
| Location known | Reject batch |
| SKU known | Quarantine row |
| Quantities non-negative and ≤ 1,000,000 | Quarantine row |

The distinction between rejecting a batch and quarantining a row is the difference between "this
warehouse is now stale" and "one SKU is missing from the total". Both are visible, neither is silent.

## State

| Key | Purpose |
| :--- | :--- |
| `cursor/{source}` | Last applied cursor |
| `last_good/{source}` | Last successful batch time |
| `snapshot/{sku}/{location}` | Current availability, mirrored to Postgres |
| `snapshot_prev1`, `prev2` | Last two batches, for the median allocation mitigation |

## Publishing

| Event | When |
| :--- | :--- |
| `stock.changed` | Per SKU whose available figure moved |
| `feed.batch.accepted` | Per batch |
| `feed.batch.rejected` | Per rejected batch |
| `feed.rows.quarantined` | Per batch with quarantine count |

## The one function

`available = on_hand - allocated - quarantine - open_reservations` lives here and is called by ATP
through the stored snapshot. It is not reimplemented in the promise service or the storefront, and a
code review rule enforces it.

## Throughput

| Source | Rows per batch | Processing |
| :--- | :--- | :--- |
| Midlands DC | 210,000 | 3.2 s |
| Glasgow DC | 96,000 | 1.6 s |
| Northgate | 2,400 | 0.4 s |
| Riverside | 1,180 | 0.3 s |
| Stores | 41,000 | 1.1 s |

Processing is streaming: a batch is validated and applied as it arrives, not held in memory whole.
That matters for the 210,000-row snapshot and for the 200 MB upload limit in the wider product.

## Metrics

| Metric | Alert at |
| :--- | :--- |
| Cycle duration | Above 8 s |
| Rejected batches | Any |
| Quarantined rows | Above 50 per cycle |
| Missed cycles | 2 in a row (warning), 3 (page) |

## Related

[Feed contracts](../../stock-feeds/protocol/feed-contracts.md) ·
[Polling and cadence](../../stock-feeds/protocol/polling-and-cadence.md) ·
[Failure and retry](../../stock-feeds/reliability/failure-and-retry.md)
