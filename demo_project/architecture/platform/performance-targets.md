# Performance Targets

Status: Draft · Owner: Nadia Kerr · Last updated: 2026-11-13

The numbers the platform must hit, why each one, and what happens if it does not. Targets are derived
from customer tolerance and peak volume, not from what the current system happens to achieve.

## Targets

| Measure | Target | Basis |
| :--- | :--- | :--- |
| Quote p95 | 180 ms | A product page has a 400 ms budget for dynamic content |
| Read p95 | 40 ms | Cached path, internal |
| Reservation p95 | 120 ms | 30 writes/s at peak, inside a 2 s order flow |
| Promise p95 | 250 ms | Includes one carrier call on a cache miss |
| Feed cycle | 8 s for 210,000 rows | 5-minute cadence leaves room |
| Order event to reservation | 2 s p95 | Reservation must precede the confirmation email |
| Error rate | 0.1 % | Below this, customers do not notice |
| Cache hit rate | 85 % | Below this, Postgres becomes the bottleneck |

## Why 180 ms

The product page renders in 400 ms. Dynamic content gets half of that, and the date is one of three
dynamic calls. 180 ms leaves headroom for the slowest of the three to be the date without pushing the
page over budget.

## Where the time goes (cache miss)

| Step | Budget | Current (UAT) |
| :--- | :--- | :--- |
| Auth and routing | 5 ms | 4 ms |
| Snapshot read | 25 ms | 18 ms |
| Open reservation count | 15 ms | 11 ms |
| Compute | 2 ms | 1 ms |
| Serialise | 4 ms | 3 ms |
| Network | 20 ms | 17 ms |
| **Total** | **71 ms** | **54 ms** |

Cache misses are comfortably inside budget; the constraint is the 420 reads per second at peak, which
is a capacity question rather than a latency one.

## Capacity

| Resource | Baseline | Peak | Headroom |
| :--- | :--- | :--- | :--- |
| ATP instances | 4 | 8 | 2× |
| Postgres CPU | 22 % | 61 % | 39 % |
| Redis memory | 1.8 GB | 4.1 GB | 5.9 GB free |
| Kafka throughput | 6 k msg/h | 12 k msg/h | 3× cluster capacity |
| Database connections | 80 | 210 | 400 limit |

## What degrades first

| Order | What happens | Customer effect |
| :--- | :--- | :--- |
| 1 | Cache hit rate falls | Latency rises to 120 ms, still fine |
| 2 | Postgres CPU above 70 % | Reservation latency rises, some timeouts |
| 3 | Connection pool saturates | Queueing, p95 above 1 s |
| 4 | Stale guard triggers | Fallback dates, stock unsellable |

The design intent is that the customer sees a slower page before they see a wrong number, and a
fallback date before an oversell.

## Testing these numbers

| Target | Test |
| :--- | :--- |
| Quote p95 | Load test at 574/s peak hour |
| Reservation throughput | Spike test, 90/s for 60 s |
| Feed cycle | Replay 210,000-row snapshot |
| Cache hit rate | Steady-state load, real traffic mix |
| Degradation order | Stress test until failure |

The stress test is deliberate: the platform's behaviour while failing matters more than its behaviour
at design load, and the degradation order is asserted, not observed after the fact.

## Related

[Performance testing](../../customer-testing/non-functional/performance-testing.md) ·
[Load profile](../../customer-testing/non-functional/load-profile.md) ·
[Availability and SLOs](./availability-and-slos.md)
