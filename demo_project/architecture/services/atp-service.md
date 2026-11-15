# ATP Service

Status: Draft · Owner: Nadia Kerr · Last updated: 2026-11-13

The availability service. It answers "how many can be sold" and is the only place that number is
computed, deliberately, because three implementations of one formula produced the quarantine bug.

## Responsibilities

| Does | Does not |
| :--- | :--- |
| Compute availability per SKU and location | Read Horizon |
| Serve quotes and reads | Book carriers |
| Create and release reservations (via the worker) | Own reservation state |
| Report per-warehouse freshness | Store promises |

## Request path

```text
quote → Redis (60 s) → miss → Postgres snapshot + open reservations → compute → cache → respond
```

| Step | Budget |
| :--- | :--- |
| Cache hit | 8 ms |
| Cache miss, single location | 45 ms |
| Cache miss, five locations | 120 ms |
| Reservation check | 25 ms |

## The availability formula

```text
available(sku, location) = on_hand - allocated - quarantine - open_reservations
```

One function, in one place, with one test suite. Every term is mandatory: a missing `quarantine`
field is treated as zero only with a logged warning, never silently.

## Staleness

The service knows each source's timestamp and threshold. A quote returns `degraded` when any
contributing source is stale, and `ATP_STOCK_STALE` when a reservation is attempted against it.

| Source state | Quote | Reservation |
| :--- | :--- | :--- |
| All fresh | Normal | Allowed |
| One source stale, others available | Normal, `degraded=false` | Allowed, from fresh sources |
| Riverside stale but inside its 45-minute limit | `degraded=true` | Allowed |
| All contributing sources stale | No date | Refused |

## Caching

| Layer | TTL | Invalidation |
| :--- | :--- | :--- |
| Redis snapshot | 60 s | `stock.changed` event |
| Gateway response | 15 s | Time only |
| Reservation path | None | Always authoritative |

The reservation path bypasses cache entirely. A reservation decided on a 59-second-old cache would be
a reservation decided on data the feed has already contradicted.

## Failure behaviour

| Failure | Behaviour |
| :--- | :--- |
| Redis unavailable | Read from Postgres, p95 900 ms, no wrong answers |
| Postgres failover | 30 s of write errors, retried by callers |
| Feed stale | Degraded or stale responses, never invented numbers |
| Ingestor down | Last snapshot served with `degraded`, then stale |

## Deployment

| Property | Value |
| :--- | :--- |
| Instances | 4 (UAT), 8 (production) |
| Autoscaling | CPU 60 %, minimum 4 |
| Database | Postgres, one primary, one read replica |
| Release | Blue/green, 5-minute observation |
| Rollback | Previous revision within 3 minutes |

## Metrics

| Metric | Alert at |
| :--- | :--- |
| Quote p95 | 250 ms |
| Read p95 | 80 ms |
| Error rate | 1 % |
| Cache hit rate | Below 70 % |
| Reservation refusal rate | Above 2 % |

## Related

[ATP service contract](../../reservation-policy/specification/atp-service-contract.md) ·
[Availability API](../../reference/api/availability-api.md) ·
[Performance targets](../platform/performance-targets.md)
