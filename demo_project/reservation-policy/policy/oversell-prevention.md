# Oversell Prevention

Status: Agreed · Owner: Sofia Mendes · Last updated: 2026-11-06

Oversell means we accepted an order for stock we could not dispatch. Today it happens to 2.1 % of
orders, costs about £38,000 a month in refunds and goodwill, and is the programme's headline
metric. This document says what prevents it, and what still does not.

## The five mechanisms

| Mechanism | What it stops | Where it lives |
| :--- | :--- | :--- |
| Reserve at payment authorisation | Two customers buying the last unit | RSV-01 |
| Per-warehouse availability | Selling stock that is in the wrong building | ATP contract |
| Stale-stock guard | Selling against a feed that stopped updating | RSV-12 |
| Quarantine exclusion | Selling damaged or held stock | RSV-13 |
| Allocation check at wave build | Picking a unit that no longer exists | Warehouse integration |

None of these is sufficient alone. Reservations without fresh stock still oversell; fresh stock
without reservations oversell under concurrency; both without allocation checks oversell when a
warehouse loses a pallet.

## The stale-stock guard

This is the mechanism that has changed most during design. A warehouse feed carries a timestamp;
if the last successful update is older than the warehouse's threshold, availability for that
warehouse returns `ATP_STOCK_STALE` instead of a number.

| Warehouse | Threshold | Behaviour when breached |
| :--- | :--- | :--- |
| Midlands DC | 15 min | Exclude from availability; site shows fallback date |
| Glasgow DC | 15 min | Exclude from availability |
| Northgate Fulfilment | 20 min | Exclude, but only for that warehouse's SKUs |
| Riverside Logistics | 45 min | Keep last known value and mark it degraded |
| Store network | 90 min | Exclude from collection promises only |

The thresholds are roughly three feed cycles, so a single missed poll does not remove a warehouse
from sale. Riverside gets a longer threshold because its snapshot generation takes 11 minutes and a
15-minute threshold would remove bulky stock from sale every day.

## What still goes wrong

| Remaining path | Why it survives | Mitigation |
| :--- | :--- | :--- |
| A unit is stolen and not written off | Feeds report what the system believes | Cycle counts; accuracy programme |
| Two warehouses claim the same transferred pallet | Transfer confirmation is manual today | Transfer reason codes; reconciliation job |
| A wave is built against reservations that expire at the same moment | Expiry and allocation race | Expiry job runs 10 s after allocation window, not before |
| Marketplace sells during a full-stock resync | Marketplace has no reservation concept | Five-minute push; conservative marketplace buffer |
| Manual override releases stock without a check | People can always do this | Reason code, daily report, no silent overrides |

## Measurement

| Metric | Definition | Target | Today |
| :--- | :--- | :--- | :--- |
| Oversell rate | Lines cancelled with `NO_STOCK_AFTER_ORDER` ÷ lines ordered | ≤ 0.4 % | 2.1 % |
| Phantom stock incidents | Store or warehouse cannot find a reserved unit | ≤ 40/day | 190/day |
| Reservation conflict rate | Two reservations attempting the same unit | 0 | Not measured today |
| Stale availability minutes | Minutes per day any warehouse is excluded | ≤ 30/week | Not measured |

The fourth metric is new and deliberately included: a system that prevents oversell by hiding stock
is not a success, so the time spent excluding a warehouse is reported to the steering group.

## The manual hold switch

If a warehouse's data is doubtful and the automatic guard is not catching it, Marcus Feld can hold a
warehouse with a reason. New reservations stop, existing ones continue, and the site shows the
fallback date for that warehouse's stock. It has been used twice in UAT rehearsals and is designed
to be used by one person in under a minute.

## Related

[Reservation rules](./reservation-rules.md) · [Stale stock handling](../../stock-feeds/reliability/stale-stock-handling.md) ·
[Oversell test scenarios](../../customer-testing/test-cases/oversell-scenarios.md)
