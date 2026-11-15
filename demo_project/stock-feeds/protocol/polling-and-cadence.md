# Polling and Cadence

Status: Draft · Owner: Dan Whitcombe · Last updated: 2026-11-13

How often we ask each warehouse for stock, why those numbers, and what happens when a cycle is
skipped. Cadence is a promise calculation input, not a technical preference: a 15-minute feed means
a promise based on stock up to 15 minutes old.

## The schedule

| Source | Cadence | Offset | Why this cadence |
| :--- | :--- | :--- | :--- |
| Midlands DC | 5 min (today 15) | :00, :05, … | Largest stock, fastest movers |
| Glasgow DC | 5 min | :02, :07, … | Shares the load ceiling with Midlands |
| Northgate | 5 min | :01, :06, … | 3PL API quota allows it |
| Riverside | 10 min | :03, :13, … | Vendor cannot go below 10 safely |
| Store network | 60 min file | :10 | CR-007, estate limitation |

Offsets are staggered deliberately. Five sources polling on the minute together produced a 4-second
spike in the old ingestor and a 12-second p95 on the availability read, both of which disappeared
once the polls were spread.

## What one cycle does

| Step | Time budget | Failure handling |
| :--- | :--- | :--- |
| Request batch | 2 s | Retry twice with backoff, then record a missed cycle |
| Validate | 300 ms | Reject bad rows into quarantine, keep the rest |
| Normalise and join SKUs | 1.2 s | Unmatched SKUs to a dead-letter table |
| Compute availability | 400 ms | Fail the cycle rather than publish partial |
| Publish changes | 800 ms | At-least-once delivery |

A cycle that fails before "compute" is a missed cycle. A cycle that fails after "compute" is retried
from the same batch, never recomputed, because recomputing against a newer partial state is how
duplicate events appear.

## Missed cycles

| Missed cycles | Effect | Alert |
| :--- | :--- | :--- |
| 1 | None; the stale threshold allows two | None |
| 2 | Warehouse marked `degraded` | Warning to the platform channel |
| 3 or more | Warehouse excluded from availability | Page the on-call engineer |

For Midlands at a 5-minute cadence, exclusion happens 15 minutes after the last good batch, which is
the same threshold as today's 15-minute cadence and therefore no regression in the worst case.

## Why not push

Three of the five sources cannot push: DC-WMS is a database view, StoreStock is a file, and
Riverside's LogiCore has no webhook. Where push is possible (Northgate supports it), we still poll,
because a push needs an endpoint we expose to a third party and a retry policy they control. Polling
is boring and boring is what a promise needs.

## Backpressure

At peak, availability reads reach 420 per second and polls compete for the same database. Polls are
given priority; reads fall back to the 60-second cache. If a poll cycle takes more than 8 seconds,
the next cycle is delayed rather than queued, so the system degrades by becoming staler rather than
by falling over.

## Related

[Feed contracts](./feed-contracts.md) · [Latency budget](../reliability/latency-budget.md) ·
[Performance targets](../../architecture/platform/performance-targets.md)
