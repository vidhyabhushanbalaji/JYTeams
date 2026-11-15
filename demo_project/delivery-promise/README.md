# Delivery Promise

Status: In review · Owner: Gavin Shore · Last updated: 2026-11-13

The promise has two halves: **can we sell it** (availability) and **when will it arrive** (the
date). This workstream owns the second half, and the number that judges the whole programme:
promise accuracy, today 71 %, target 92 % by the end of 2027.

## What the promise is

One date, computed once, used everywhere: product page, basket, checkout, confirmation email,
contact centre screen and marketplace dispatch expectation. Four different promises for one order is
the failure the platform exists to remove.

## How the date is built

| Input | Source | Example |
| :--- | :--- | :--- |
| Warehouse that can serve | Availability | Midlands DC |
| Cut-off for that warehouse and service | Carrier rules | 15:00 parcels |
| Carrier lead time | Carrier contract | Next working day |
| Serviceability of the postcode | Carrier API | `CV21` served next-day |
| Business calendar | Platform | Excludes 25–26 December |
| Bank holiday buffer | Policy | +6 hours (RSV-19) |

The full calculation, including the order of operations and the rounding rule, is in
[delivery date logic](./calculation/delivery-date-logic.md).

## Where each part lives

| Question | Document |
| :--- | :--- |
| Which carriers, and what can they do? | [Carriers](./carriers/) |
| How is the date computed? | [Delivery date logic](./calculation/delivery-date-logic.md) |
| What are the cut-offs? | [Cut-off times](./calculation/cut-off-times.md) |
| What service levels do we sell? | [Service levels](./calculation/service-levels.md) |
| Holidays and peak | [Peak and holiday calendar](./calculation/peak-and-holiday-calendar.md) |
| When can we not promise? | [Unavailable dates](./calculation/unavailable-dates.md) |
| What does the customer see? | [Customer messaging](./customer-messaging/) |
| How accurate are we? | [Promise accuracy](./customer-messaging/promise-accuracy.md) |

## The customer-facing rules

1. A date is shown only when the platform can defend it from stock, cut-off and carrier data.
2. If any input is stale or missing, the fallback estimate is shown instead of a date.
3. A date that changes is notified, not quietly updated (CR-009, in review).
4. Dates are shown as a day, never as a range, unless the fallback is in use.
5. Collection shows "ready from" and never a delivery date.

## Status

| Area | State | Note |
| :--- | :--- | :--- |
| Parcelway integration | Sandbox live | Booking and serviceability tested |
| Northline integration | Sandbox agreed | Two-person slot API, capacity feed pending |
| Swiftbox integration | Contract signed | Locker availability feed from January |
| Date calculation | Design agreed | Depends on RSV-06 for bulky |
| Messaging | Draft | Legal review for fallback wording (DEP-08) |
| Accuracy measurement | Running | Baseline 71 %, measured weekly |

## Related

[Availability API](../reference/api/availability-api.md) · [Delivery promise API](../reference/api/delivery-promise-api.md) ·
[Promise accuracy](./customer-messaging/promise-accuracy.md)
