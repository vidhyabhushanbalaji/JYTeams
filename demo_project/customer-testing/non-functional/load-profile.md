# Load Profile

Status: Agreed · Owner: Nadia Kerr · Last updated: 2026-11-13

The traffic model behind the performance tests: how many requests, of what kind, at which hours, with
what shape. It is built from October 2026 production data and the November 2025 peak.

## Daily shape

| Hour | Quotes/s | Reads/s | Reservations/s | Note |
| :--- | :--- | :--- | :--- | :--- |
| 00:00–06:00 | 6 | 3 | 0.2 | Batch window |
| 06:00–09:00 | 38 | 18 | 2.1 | Morning browse |
| 09:00–12:00 | 92 | 44 | 5.8 | Building |
| 12:00–14:00 | 128 | 61 | 7.9 | Lunch peak |
| 14:00–18:00 | 104 | 50 | 6.4 | Afternoon |
| 18:00–22:00 | 151 | 72 | 8.2 | Evening peak |
| 22:00–00:00 | 44 | 21 | 2.3 | Taper |

Baseline day total: 13,590 orders, 512,000 availability quotes.

## Peak day (Black Friday shape)

| Metric | Baseline | Peak | Multiple |
| :--- | :--- | :--- | :--- |
| Orders | 13,590 | 52,000 | 3.8× |
| Quotes | 512,000 | 1,940,000 | 3.8× |
| Quotes/s at peak hour | 151 | 574 | 3.8× |
| Reservations/s at peak | 8.2 | 31 | 3.8× |
| Feed messages/hour | 6,100 | 12,000 | 2.0× |
| Concurrent users | 9,400 | 34,000 | 3.6× |

The feed multiple is lower than the order multiple because feeds reflect stock changes, which do not
scale with orders as sharply (many orders hit the same SKUs).

## Spike shape

Promotion starts produce a burst rather than a ramp:

| Second | Quotes | Note |
| :--- | :--- | :--- |
| 0–5 | 180 | Email lands |
| 5–30 | 260 | Sustained spike |
| 30–60 | 190 | Settles |
| 60–120 | 120 | Normalises |

The system must absorb 90 order events per second for 60 seconds, which is the burst in the acceptance
criteria (AC-20).

## Hot SKUs

| Rank | Share of orders | Consequence |
| :--- | :--- | :--- |
| Top 10 SKUs | 12 % | Reservation contention |
| Top 200 SKUs | 44 % | Cache hot set |
| Long tail | 56 % | Cache misses |

Load tests include a 200-SKU hot set, because a uniform distribution would understate contention by
an order of magnitude.

## Test data volume

| Table | Rows at peak |
| :--- | :--- |
| Stock records | 556,000 |
| Open reservations | 38,000 |
| Promise records | 620,000 (30-day horizon) |
| Order events per hour | 6,500 |
| Feed events per hour | 12,000 |

Postgres and Redis are sized for these numbers with 40 % headroom, which is checked in the April
stress test rather than assumed.

## Assumptions that could be wrong

| Assumption | If wrong | Headroom |
| :--- | :--- | :--- |
| 3.8× peak multiple | A 5× peak breaks the plan | Instance count, not code |
| 44 % of orders on 200 SKUs | More concentration increases contention | Row-level locking tuned |
| 40 % headroom | A larger catalogue increases rows | Vertical scale available |
| Peak lasts 8 hours | A multi-day surge tests soak behaviour | Soak test covers 8 hours |

## Related

[Performance testing](./performance-testing.md) · [Order volume baseline](../../current-state/channels/order-volume-baseline.md) ·
[Scalability](../../architecture/platform/performance-targets.md)
