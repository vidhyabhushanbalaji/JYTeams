# 0002 — Event-Driven Stock Updates

Status: Accepted · Date: 2026-10-09 · Deciders: Nadia Kerr, Dan Whitcombe

## Context

Stock currently moves as snapshots: a full extract every 15 minutes, queued through Orbit, applied to
Mercury, then re-extracted for marketplaces. The end-to-end age of a stock figure is between 30 minutes
and 14 hours, and the pipeline has no per-message visibility, which is why F-04 took six hours to
notice.

## Options

| Option | Latency | Observability | Cost |
| :--- | :--- | :--- | :--- |
| A. Keep snapshots, shorten cadence | 5–10 min | None | Cheap |
| B. Events with a bus | ~1 s after batch | Per-message | Kafka plus skills |
| C. Direct database replication | Real time | Poor | Couples us to each WMS |
| D. Warehouse webhooks | Real time | Per-message | Three of five vendors cannot |

## Decision

Publish **`stock.changed` events on a managed Kafka cluster**, one per SKU whose availability actually
moved, and keep batch pulls as the transport from each warehouse.

## Why not shorter snapshots

Option A was the obvious cheap answer and it fails twice. First, 210,000 rows every 5 minutes is 42,000
rows a second of write amplification for maybe 400 real changes. Second, it keeps the Mercury round trip,
which costs six minutes on its own and hides failures inside a batch.

## Consequences

| Easier | Harder |
| :--- | :--- |
| Per-SKU events with ordering guarantees | Operating Kafka with a two-person team |
| Cursor and sequence checks per batch | Schema versioning discipline |
| Replay for incident review | Consumer idempotency everywhere |
| Sub-second propagation to caches | Two transports to understand: batch in, events out |

The operating burden is mitigated by Cortex Partners for the first year, but it is a real cost and it
appears in the resourcing plan rather than being assumed away.

## Why keep polling inbound

Only Northgate can push. DC-WMS is a SQL view, StoreStock is a file, and LogiCore has no webhook.
Pretending otherwise would have produced a design that works for one vendor and not the others.

## Related

[Feed contracts](../stock-feeds/protocol/feed-contracts.md) ·
[Reservation events](../reservation-policy/specification/reservation-events.md) ·
[ADR 0006](./0006-redis-cache-with-short-ttl.md)
