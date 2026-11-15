# Performance Testing

Status: Draft · Owner: Nadia Kerr · Last updated: 2026-11-13

Three targets decide whether the platform survives a normal Tuesday and a Black Friday: availability
lookup latency, reservation throughput, and feed processing time. Everything else is secondary.

## Targets

| Measure | Target | Peak rationale |
| :--- | :--- | :--- |
| Availability quote p95 | ≤ 180 ms | 420 lookups/second at peak |
| Availability read p95 | ≤ 40 ms | Cached product pages |
| Reservation p95 | ≤ 120 ms | 30 writes/second at peak |
| Reservation success rate | ≥ 99.5 % | Under normal load |
| Feed cycle p95 | ≤ 8 s per source | 210,000 rows worst case |
| Order event to reservation | ≤ 2 s p95 | The promise's freshness |
| Error rate | ≤ 0.1 % | All endpoints |
| Memory growth over 8 hours | ≤ 5 % | No leak |

## Test types

| Type | Purpose | Duration | When |
| :--- | :--- | :--- | :--- |
| Baseline | Single user, cold cache | 10 min | Every release |
| Load | Peak hour, sustained | 1 hour | Weekly from March |
| Stress | Until failure, find the knee | 30 min | Once, in April |
| Soak | 8 hours at 60 % peak | 8 hours | Twice |
| Spike | 90 events/second for 60 s | 5 min | Every release |
| Feed burst | All five sources at once | 15 min | Every release |

## What the tests actually call

| Endpoint | Mix | Notes |
| :--- | :--- | :--- |
| `POST /availability/quote` | 72 % | 1–4 lines per request |
| `GET /availability/{sku}` | 20 % | Cached |
| `POST /reservations` | 5 % | Real reservation worker path |
| `POST /reservations/{id}/release` | 2 % | — |
| `GET /health` | 1 % | — |

The mix comes from the October traffic profile, not from an estimate. Testing a uniform mix produces
a system that is fast at the wrong thing.

## Pass and fail

| Result | Meaning |
| :--- | :--- |
| Within p95 targets, error rate ≤ 0.1 %, no leak | Pass |
| Within targets but error rate 0.1–1 % | Fail: errors are customer-visible |
| p95 over target but average fine | Fail: the tail is the experience |
| Any wrong availability answer under load | Fail, regardless of latency |
| Recovery after stress without restart | Required |

The fourth row is the one that matters most: a platform that gets faster by returning stale or wrong
availability has failed, whatever the dashboard says.

## Environment caveat

UAT has 4 application instances and production has 8, so UAT results are scaled by a documented
factor of 1.9 and then verified against staging. Scaling results is inexact, which is why the stress
test in April runs in staging with production-like capacity rather than in UAT.

## What we do not measure

| Not measured | Why |
| :--- | :--- |
| Marketplace API response time | Vendor-controlled, budgeted separately |
| Warehouse system latency | Outside our control, covered by feed contracts |
| Carriers | Sandboxes are not representative |
| Store device performance | Estate programme, not platform |

## Related

[Load profile](./load-profile.md) · [Performance targets](../../architecture/platform/performance-targets.md) ·
[Availability and SLOs](../../architecture/platform/availability-and-slos.md)
