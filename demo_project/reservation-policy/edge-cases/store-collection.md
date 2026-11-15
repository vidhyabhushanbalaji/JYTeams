# Store Collection

Status: In review · Owner: Elena Vasquez · Last updated: 2026-11-13

Click and collect is 1,100 orders a day and the least reliable promise we make: 18 % of collection
orders are cancelled because the store cannot find the item. The reservation is what turns "the
system thinks it is there" into "the store has been asked to pick it".

## The flow

| Step | Who | What happens | Reservation state |
| :--- | :--- | :--- | :--- |
| 1 | Customer | Chooses a store at checkout | None yet |
| 2 | Platform | Reserves the unit in that store's pool | `SOFT`, 30 min |
| 3 | Platform | Sends a pick task to the store's task list | `SOFT` |
| 4 | Store colleague | Picks the item, scans it | `ALLOCATED` |
| 5 | Platform | Emails "ready to collect" | `ALLOCATED` |
| 6 | Customer | Collects within the window | `DISPATCHED` |
| 7 | Platform | Window passes | `RELEASED`, `NOT_COLLECTED` |

## The pick reservation is only 30 minutes, the hold is 5 days

Two different clocks, and they are easy to confuse:

- The **pick reservation** is 30 minutes: the store must accept and pick within half an hour, or the
  unit is released back to store stock. Without this, an unstaffed store could hold stock forever.
- The **collection hold** is 5 days from the "ready to collect" email (RSV-11 is the open decision
  on whether 5 days should become 3).

Uncollected orders are a real cost: 7 % of collection orders are never collected, and the refund and
restock cycle takes six days on average.

## Why 24 hours matters

If a store has not picked within 24 hours (RSV-08), the store task becomes a reminder and the
customer is not contacted yet, because the item is usually found. At 24 hours the store's area
manager is copied. In the pilot stores this moved the pick rate within 24 hours from 71 % to 89 %.

## The accuracy caveat

Store stock is 91 % accurate, so 9 % of collection reservations are for stock that does not exist.
The reservation cannot fix that. What it does is surface the failure earlier: the store discovers it
at pick time, within 30 minutes of the order, instead of the next morning when the file updates. The
customer is told sooner, and the unit is released so someone else can buy it if it does exist.

| Outcome | Today | Target after launch |
| :--- | :--- | :--- |
| Cancelled within 1 hour | 22 % of failures | 70 % of failures |
| Cancelled within 24 hours | 55 % | 28 % |
| Never told until customer arrives | 23 % | 2 % |

## What stores asked for

1. A pick task they can see on the handheld, not a printout.
2. The customer's name and order number on the task.
3. A way to say "found a different one" without cancelling.
4. A reminder that clears itself.

Items 1 and 2 are in scope; 3 is in scope as a substitution flow limited to the same SKU; 4 is a
configuration of the store task list and not a platform change.

## Related

[Store channel](../../current-state/channels/stores.md) · [Store stock feed](../../stock-feeds/warehouses/store-stock-network.md) ·
[Collection test scenarios](../../customer-testing/test-cases/store-collection-scenarios.md)
