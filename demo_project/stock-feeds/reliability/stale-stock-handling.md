# Stale Stock Handling

Status: Agreed · Owner: Dan Whitcombe · Last updated: 2026-11-13

The most important behaviour in the platform is what it does when it does not know something. Stale
stock is not an error condition to be logged; it is a customer-facing state that changes what we
promise.

## What stale means

A source is stale when its most recent **successful, complete** batch is older than its threshold,
measured on `batch_timestamp`. Arrival time is irrelevant: a batch that arrives on time with an
hour-old timestamp is stale.

| Source | Threshold | Reasoning |
| :--- | :--- | :--- |
| Midlands DC | 15 min | Three cycles at a 5-minute cadence |
| Glasgow DC | 15 min | Same |
| Northgate | 20 min | Three cycles plus the vendor's 3.8 s generation time |
| Riverside | 45 min | Three cycles at 10 min, plus the 11-minute snapshot |
| Stores | 90 min | One hourly cycle plus load time |

## What happens when a source is stale

| Audience | Behaviour |
| :--- | :--- |
| Availability quote | Excludes the source, or marks `degraded` where the threshold allows |
| Storefront | Shows the fallback delivery estimate, not a date |
| Reservation | Refuses with `ATP_STOCK_STALE` (RSV-12) |
| Warehouse system | Nothing; it does not know and does not need to |
| Operations | Alert at two missed cycles; page at three |

The reservation refusal is deliberate and occasionally painful: a customer can be told "we cannot
confirm a date right now" while stock physically exists. Sofia's position, agreed at the October
workshop, is that refusing is better than guessing, because a guess becomes a broken promise and a
call to the contact centre.

## The three levels

| Level | Condition | Customer-visible effect |
| :--- | :--- | :--- |
| Fresh | Within threshold | Normal promise |
| Degraded | 1–2 cycles late, or a source excluded with others available | Promise from the remaining sources, `degraded=true` |
| Unavailable | All sources for a SKU stale, or three cycles late | Fallback estimate, no reservation |

`degraded` is deliberately not hidden. The storefront adds a line to the delivery panel explaining
that the date may change, which is a compromise between saying nothing and alarming the customer.

## Why Riverside is different

Riverside keeps serving its last known value for up to 45 minutes rather than being excluded,
because bulky stock does not move quickly: 1,200 SKUs, a delivery-run allocation model, and a
median of 14 units sold per SKU per week. Removing it from sale would cost more than a slightly old
figure, and the promise for bulky goods already includes a five-day lead time that absorbs it.

## Manual intervention

Marcus Feld can hold a warehouse (RSV-18), which stops new reservations without releasing existing
ones. The hold is a separate control from staleness because it is used for reasons the system cannot
detect: a suspected data problem, a physical incident, a carrier failure.

| Control | Actor | Effect | Reversible |
| :--- | :--- | :--- | :--- |
| Automatic stale exclusion | Platform | Source removed from availability | Yes, on next good batch |
| Degraded flag | Platform | Date shown with a caveat | Yes |
| Manual hold | Marcus Feld | No new reservations at that warehouse | Yes, manual release |
| Full platform hold | Nadia Kerr | No reservations at all; site shows estimates | Yes, manual release |

## Measurement

| Metric | Target | Why |
| :--- | :--- | :--- |
| Minutes of exclusion per source per week | ≤ 30 | A platform that prevents oversell by hiding stock is not a success |
| Batches missed per source per month | ≤ 2 | Separates vendor reliability from our polling |
| Reservations refused as stale | ≤ 0.5 % of attempts | If this rises, the cadence is too slow |

## Related

[Latency budget](./latency-budget.md) · [Oversell prevention](../../reservation-policy/policy/oversell-prevention.md) ·
[Stock feed failure runbook](../../launch-readiness/runbooks/stock-feed-failure.md)
