# Order Volume Baseline

Status: Agreed · Owner: Dan Whitcombe · Last updated: 2026-10-28

The numbers the platform has to be designed for. All figures are an October 2026 average across
four weeks, with peak taken from the November 2025 trading period as a proxy for 2027.

## By channel

| Channel | Orders/day | Share | Average value | Split-ship | Oversell | Peak multiple |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| Website | 7,400 | 52 % | £68 | 41 % | 2.4 % | 3.6× |
| Amazon UK | 3,700 | 26 % | £54 | 34 % | 1.8 % | 4.1× |
| eBay UK | 1,150 | 8 % | £41 | 29 % | 2.9 % | 3.2× |
| Stores and collection | 1,100 | 8 % | £52 | 6 % | 1.2 % | 2.8× |
| Wholesale | 240 | 2 % | £640 | 12 % | 0.4 % | 1.9× |
| **Total** | **13,590** | **100 %** | **£71** | **38 %** | **2.1 %** | **3.7×** |
| Other (manual, goodwill) | 610 | — | — | — | — | — |
| **Grand total** | **14,200** | — | — | — | — | — |

## What peak looks like

Black Friday week 2025 produced **52,000 orders in a day**, 3.7× the October baseline, with 71 % of
them in the first eight hours. The platform's targets are set against that day, not the average:

| Target | Value | Why |
| :--- | :--- | :--- |
| Sustained order events | 25 per second | Peak hour on Black Friday |
| Burst order events | 90 per second for 60 seconds | Promotion start |
| Availability lookups | 420 per second | Product page traffic at peak |
| Reservation writes | 30 per second | Orders plus collection holds |
| Feed messages | 12,000 per hour | All five sources in a burst |

## Stock movement

| Metric | Value | Note |
| :--- | :--- | :--- |
| Active SKUs | 31,400 | Atlas, sellable in at least one channel |
| SKUs stocked in more than one warehouse | 8,900 | Where split shipments come from |
| Stock records per warehouse feed | 60,000–210,000 | Midlands DC is the largest |
| Adjustments per day | 4,800 | Merchandising, damage, cycle counts |
| Reservations expected at peak | 38,000 open | At 30-minute expiry, roughly |

## How this was measured

Mercury order tables for 1–28 October 2026, cross-checked against channel settlement reports and
the Horizon stock ledger. Oversell is defined as an order line cancelled with reason
`NO_STOCK_AFTER_ORDER`. Split-ship is defined as more than one dispatch against one order.

## What this means for design

The volume is not large by platform standards, which is why a single Postgres instance behind two
services is enough. The hard part is **concurrency on a single SKU**: 31,400 SKUs, but the top 200
account for 44 % of orders, so reservation contention concentrates on a small hot set. That is
addressed in [ADR 0002](../../decisions/0002-event-driven-stock-updates.md) and
[ADR 0006](../../decisions/0006-redis-cache-with-short-ttl.md).

## Related

[Website](./website.md) · [Batch windows](../order-flow/batch-windows.md) ·
[Load profile](../../customer-testing/non-functional/load-profile.md)
