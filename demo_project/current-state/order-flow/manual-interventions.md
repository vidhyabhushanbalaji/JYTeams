# Manual Interventions

Status: Agreed · Owner: Marcus Feld · Last updated: 2026-11-03

The system does not cope with about 3 % of orders, so people do. This document lists the manual
work that keeps the business running, who does it, and what it costs, because every one of these
is a candidate for removal by Truestock, and each one hides a rule the new system would need.

## The five jobs

| Job | Who | Volume | Time per item | Daily effort |
| :--- | :--- | :--- | :--- | :--- |
| Stock adjustment from the shelf | Merchandising (4 people) | 310 adjustments | 4 min | 20.7 h |
| Order hold and release | Customer operations (3 people) | 25 orders | 12 min | 5.0 h |
| Store transfer correction | Store support (2 people) | 46 transfers | 9 min | 6.9 h |
| Backorder chase | Wholesale desk (2 people) | 22 lines | 15 min | 5.5 h |
| "Cannot find item" resolution | Contact centre (rotating) | 74 calls | 6 min | 7.4 h |
| **Total** | **11 people, partly** | — | — | **45.5 h/day** |

## Stock adjustment from the shelf

The most consequential job. A store finds five more of a SKU than the system believes, or a
warehouse finds a pallet that was never booked in, and someone types the correction into Mercury.
There is no approval step and no audit trail beyond the Mercury change log, which is retained for
30 days.

Two things follow. First, the correction applies immediately to the website, so a typo can create
ten phantom sales. Second, the correction is invisible to Horizon until the nightly ledger post, so
finance and operations disagree about stock for up to 24 hours every day.

## Order hold and release

Twenty-five orders a day are held for address checks, suspected fraud or a customer request. The
hold is a free-text flag; releasing it is a manual status change that does not re-check stock.
Releasing a three-day-old hold routinely produces an oversell.

## Store transfer correction

When stock moves between stores, the sending store records the transfer and the receiving store is
supposed to confirm. 46 transfers a day are not confirmed, so store support corrects them by hand.
This is the largest single cause of the 6 % of store stock that is simply wrong at any moment.

## Backorder chase

Wholesale backorders are chased by email. When stock arrives, the desk allocates it by hand in
order of customer importance, not order date. There is no rule written down for "importance", which
makes this the hardest manual process to replace.

## "Cannot find item" resolution

Collection orders the store cannot find are resolved by the contact centre: call the store, check
the shelf, cancel or re-promise. 74 calls a day at six minutes each, and the customer has usually
already been told the item was there.

## What Truestock removes, and what it cannot

| Job | Effect under Truestock |
| :--- | :--- |
| Stock adjustment | Stays, but gains an approval step and an audit trail |
| Order hold and release | Reduced; hold releases re-check availability |
| Store transfer correction | Reduced by the hourly store feed, not removed |
| Backorder chase | Unchanged; wholesale rules are out of scope this release |
| Cannot find item | Reduced by store reservation at pick time |

The honest position is that the platform removes about 40 % of the manual effort, mostly in the
last two rows, and the rest becomes better controlled rather than smaller.

## Related

[Routing rules](./routing-rules.md) · [Known failures](./known-failures.md) ·
[Reservation lifecycle](../../reservation-policy/policy/reservation-lifecycle.md)
