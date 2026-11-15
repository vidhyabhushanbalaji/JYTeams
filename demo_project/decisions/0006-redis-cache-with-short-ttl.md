# 0006 — Redis Cache with a 60-Second TTL

Status: Accepted · Date: 2026-10-09 · Deciders: Nadia Kerr, Dan Whitcombe

## Context

Peak product browsing produces 420 availability reads per second for 31,400 SKUs, with 44 % of orders
concentrated on 200 of them. Serving every read from Postgres would work at 80 ms, but it would put the
database on the critical path of the busiest page on the site.

## Options

| Option | Read latency | Freshness | Complexity |
| :--- | :--- | :--- | :--- |
| A. Redis, 60 s TTL | 8 ms | Up to 60 s old | One more component |
| B. Postgres read replica | 30–45 ms | Current | Simpler |
| C. No cache, primary only | 45–80 ms | Current | Simplest, highest load |
| D. Long TTL, invalidate on change | 8 ms | ~1 s | Invalidation must be perfect |

## Decision

Cache the computed availability in **Redis with a 60-second TTL**, invalidated by `stock.changed`, and
never cache the reservation path.

## Why not invalidation-only

Option D is strictly better on paper and worse in practice: a missed invalidation serves a stale number
indefinitely, with no upper bound. A TTL means the worst case is 60 seconds, which the latency budget
already accounts for. Defence in depth, where the cache is allowed to be briefly wrong but never
indefinitely wrong.

## Consequences

| Easier | Harder |
| :--- | :--- |
| 8 ms reads, Postgres below 25 % CPU | Another component to run and alert on |
| Cache absorbs promotional bursts | Cache stampede after a restart |
| Queries per second scale linearly | Invalidation bugs are invisible |
| Degradation to database is defined | A second consistency model to reason about |

## The stampede

Cold start after a restart sends every read to Postgres at once. Mitigations: staggered pod restarts,
a single-flight loader per SKU, and a 30-second warm-up window during deployments where the cache is
pre-populated from the hot 200 SKUs.

## Consequences for correctness

`degraded` is returned when the underlying feed was already stale at the time the cached value was
computed. A cache hit is never presented as fresh data; it is presented as data up to 60 seconds old,
which is exactly what the promise calculation assumes.

## Related

[ATP service](../architecture/services/atp-service.md) ·
[Performance targets](../architecture/platform/performance-targets.md) ·
[ADR 0002](./0002-event-driven-stock-updates.md)
