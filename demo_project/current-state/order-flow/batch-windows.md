# Batch Windows

Status: Agreed · Owner: Dan Whitcombe · Last updated: 2026-11-03

Almost everything that matters today runs on a schedule, and the schedules collide. This is the
inventory of jobs, their windows and the collisions that produce the failures described in
[known failures](./known-failures.md).

## Daily schedule (UK time)

| Time | Job | System | Duration | Feeds |
| :--- | :--- | :--- | :--- | :--- |
| 00:05 | Stock extract | Mercury | 12 min | ChannelBridge, store portal |
| 00:20 | Marketplace inventory push | ChannelBridge | 9 min | Amazon, eBay |
| 00:40 | Order routing run | Mercury | 46 min | All warehouses |
| 01:00 | Stock ledger posting | Horizon | 70 min | Finance only |
| 02:00 | Northgate WMS maintenance | StockFlow | 20 min | Feed unavailable |
| 02:30 | Feed poll: Midlands, Glasgow | Orbit | 6 min | Mercury |
| 02:45 | Feed poll: Riverside | Orbit | 4 min | Mercury |
| 03:00 | Dispatch notes | Mercury | 18 min | All warehouses |
| 06:00–22:00 | Feed poll every 15 min | Orbit | 90 s | Mercury |
| 23:30 | Store stock file | StoreStock | 41 min | Mercury |
| 23:30 | Returns and restock file | Mercury | 11 min | All warehouses |

## The collisions

| Collision | Window | Effect |
| :--- | :--- | :--- |
| Mercury extract vs routing run | 00:05–01:26 | Routing reads a snapshot that is already 80 minutes old |
| Horizon ledger write vs stock extract | 01:00–02:10 | Stock figures can include a posting that is later reversed |
| Northgate maintenance vs feed poll | 02:00–02:20 | Two failed polls every night (ISSUE-014) |
| Store file vs all other feeds | 23:30–00:11 | The store file load blocks the Mercury API for 9 minutes |
| Peak order volume vs routing | 12:00–14:00 | Routing runs hourly at peak and falls behind by up to 40 minutes |

## Why this matters for the new platform

The new services are event-driven and have no batch dependency, but three of the five sources
only publish on a schedule. A 15-minute feed cadence means a promise can be based on stock that is
at most 15 minutes old, and the reservation rule has to say what is acceptable. That is why the
latency budget is a business number and not an engineering one:

| Warehouse | Cadence today | Cadence target | Maximum age used in promises |
| :--- | :--- | :--- | :--- |
| Midlands DC | 15 min | 5 min | 6 min |
| Glasgow DC | 15 min | 5 min | 6 min |
| Northgate Fulfilment | 15 min | 5 min | 6 min |
| Riverside Logistics | 15 min | 10 min | 11 min |
| Store network | 24 h | 60 min | 65 min |

## Windows we must not move

The Northgate maintenance window is contractually theirs and can only be avoided, not moved. The
Horizon ledger posting is fixed by finance month-end controls. Everything else is ours to change,
which is why the feed cadence negotiation is the whole of DEP-02 and DEP-10.

## Related

[Order capture](./order-capture.md) · [Polling and cadence](../../stock-feeds/protocol/polling-and-cadence.md) ·
[Latency budget](../../stock-feeds/reliability/latency-budget.md)
