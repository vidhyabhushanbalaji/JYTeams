# Latency Budget

Status: Agreed · Owner: Dan Whitcombe · Last updated: 2026-11-06

How old is the stock number a customer is looking at, and where does that time go? This document
breaks the path from a picker moving a box to a customer seeing a delivery date, and sets a budget
for each hop.

## The path

| Hop | What happens | Budget p95 | Today p95 |
| :--- | :--- | :--- | :--- |
| 1. Warehouse movement to export | The system notices a change | 30 s | 4 min |
| 2. Export to our poll | Cadence and timing | 5 min | 15 min |
| 3. Poll to availability computed | Validate, normalise, compute | 4 s | 40 s |
| 4. Computed to published | Event publish | 1 s | — |
| 5. Published to cache | Cache invalidation | 2 s | — |
| 6. Cache to customer render | Storefront request | 15 s | 15 s |
| **Total** | | **6 min 22 s** | **20 min 30 s** |

## What the promise may assume

The delivery promise is calculated from an availability figure, and it must declare the age it
assumed. The rule is: **the promise may not assume stock newer than the budget**, even if the feed
happens to be faster.

| Source | Age assumed in promises | Rationale |
| :--- | :--- | :--- |
| Midlands, Glasgow, Northgate | 6 min | Budget, with headroom |
| Riverside | 11 min | 10-minute cadence plus processing |
| Stores | 65 min | 60-minute file plus processing |

That assumption is why the stale thresholds are three cycles rather than one: a promise built on a
6-minute-old figure remains defensible while the feed is inside its threshold, and stops being
defensible once the figure cannot be refreshed.

## Where the time actually goes today

| Cause | Minutes | Fix |
| :--- | :--- | :--- |
| 15-minute poll cadence | 15 | 5-minute cadence (contracts) |
| Snapshot generation, Midlands | 0.2 | Delta feed |
| Orbit queueing | 3–9 | Event stream |
| Mercury batch application | 2–14 | Direct ingestion, no Mercury round trip |
| Store file | 1,440 | Hourly file (CR-007) |

The Mercury round trip is the least obvious cost: stock arrives in Orbit, is written to Mercury,
and is only then readable by anything else. Removing Mercury from the stock path saves an average of
six minutes on its own.

## What we are not promising

Real-time. A 6-minute figure is honest and achievable across five heterogeneous warehouses; a
sub-minute figure would require each warehouse to push events, which three of the five cannot do.
Advertising "live stock" would be a marketing claim the platform cannot support, and Tom Alder has
specifically ruled it out in the customer messaging.

## Measuring it

The ingestor records, per batch, `feed_timestamp`, `received_at`, `computed_at`, `published_at`.
The dashboard plots the p95 for each hop per source, and the promise service logs the assumed age
with every calculation it returns, so a wrong promise can be traced to the figure it was built on.

## Related

[Polling and cadence](../protocol/polling-and-cadence.md) · [Stale stock handling](./stale-stock-handling.md) ·
[Performance targets](../../architecture/platform/performance-targets.md)
