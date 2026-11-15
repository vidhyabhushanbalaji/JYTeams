# Northgate Fulfilment

Status: Draft · Owner: Dan Whitcombe · Last updated: 2026-11-13

Northgate is our largest 3PL, in Daventry, holding 148,000 records and fulfilling the Amazon
channel first. Its system, StockFlow, is the most capable of the five and the most contractual.

## Feed properties

| Property | Today | Contract target |
| :--- | :--- | :--- |
| Mechanism | REST delta endpoint | Same |
| Paging | 5,000 records, up to 30 pages | 2,000 records, change-driven |
| Cadence | 15 minutes | 5 minutes |
| Records per delta | ~2,400 | ~800 (smaller, faster pages) |
| Maintenance window | 02:00–02:20 nightly | Declared, excluded from staleness |
| Authentication | Static API key | OAuth client credentials |
| Contract reference | Services schedule 4, para 6 | Variation requested 2026-11-09 |

## The stock model

StockFlow distinguishes four quantities, and all four matter:

| Field | Meaning | Availability treatment |
| :--- | :--- | :--- |
| `available` | Sellable, unreserved | Included |
| `reserved_outbound` | Allocated to a Northgate wave | Excluded |
| `on_hold_client` | Northgate's own client quarantine | Never included |
| `inbound_pending` | Arriving, not booked in | Not included until booked |

`inbound_pending` is the field that creates hope and disappointment: stock physically on site,
counted by nobody, sometimes sellable tomorrow. Truestock deliberately excludes it, and the
availability response says so through `not_yet_available`, so the storefront can show "arriving
soon" without promising stock.

## The maintenance window (ISSUE-014)

Between 02:00 and 02:20 StockFlow rejects all requests. Today Orbit logs two failed polls and moves
on, which means the last good figure is 20 minutes old at 02:20 and nobody notices because it is
night. Under the new platform this becomes a declared maintenance window:

| Behaviour | Detail |
| :--- | :--- |
| Poll during window | Skipped, not retried |
| Staleness clock | Paused, not reset |
| Availability during window | Last good snapshot, marked `degraded` |
| Alerting | None; a maintenance window is not an incident |

The difference between "skipped and paused" and "failed and stale" is the whole fix, and it is why
the issue is being closed as a configuration change rather than a vendor escalation.

## Quality of the data

| Measure | Value | Note |
| :--- | :--- | :--- |
| Records matching Atlas | 99.6 % | 148,000 of 148,600 |
| SKUs with no movement in 30 days | 22 % | Seasonal and slow-moving |
| Delta accuracy vs full snapshot | 99.98 % | Verified weekly for four weeks |
| Average feed generation | 3.8 s | Well inside budget |

## What Northgate asked for

A confirmed reservation feed rather than a silent release. Today, when we release stock, Northgate
learns about it only when it next polls, and its own allocation may already have claimed the unit.
The integration hub now sends `reservation.released` events, and StockFlow has agreed to consume
them from 2027-02 in a patch release.

## Related

[Warehouse systems](../../current-state/systems/warehouse-systems.md) · [Failure and retry](../reliability/failure-and-retry.md) ·
[Feed incidents](../reliability/feed-incidents.md)
