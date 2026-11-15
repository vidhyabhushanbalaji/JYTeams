# Reservation Lifecycle

Status: Agreed · Owner: Sofia Mendes · Last updated: 2026-11-13

Every unit of stock that is promised to a customer moves through five states. This is the canonical
description of those states; the services implement exactly this and nothing more.

## States

| State | Meaning | Counts against availability | Warehouse aware |
| :--- | :--- | :--- | :--- |
| `AVAILABLE` | No claim on the unit | No | No |
| `SOFT` | Promised to an order, not yet picked | Yes | No |
| `ALLOCATED` | Accepted by a warehouse into a pick wave | Yes | Yes |
| `DISPATCHED` | Left the building | Yes (leaves the feed) | Yes |
| `RELEASED` | Claim withdrawn, with a reason | No | At next poll |
| `EXPIRED` | Claim timed out | No | At next poll |

`RELEASED` and `EXPIRED` are terminal for a reservation record but not for the stock: the same unit
can be reserved again by a new order, with a new reservation ID.

## Transitions

| From | To | Trigger | Actor | Maximum delay |
| :--- | :--- | :--- | :--- | :--- |
| `AVAILABLE` | `SOFT` | Payment authorised | Reservation worker | 2 s from the order event |
| `SOFT` | `ALLOCATED` | Warehouse accepts a pick wave | Warehouse system | Up to the wave build |
| `SOFT` | `RELEASED` | Order cancelled or payment failed | Reservation worker | 2 s from the event |
| `SOFT` | `EXPIRED` | 30 minutes elapse without confirmation | Expiry job | 60 s |
| `ALLOCATED` | `DISPATCHED` | Dispatch event from Mercury | Integration hub | 5 min |
| `ALLOCATED` | `RELEASED` | Warehouse rejects the line or order cancelled | Reservation worker | 2 s from the event |

## The 30-minute window

The soft reservation lasts 30 minutes from authorisation. That number comes from payment behaviour:
97.4 % of card authorisations are captured within 20 minutes, and the 30-minute window covers
capture plus one retry. At peak the window is **not** extended, because a longer hold on a hot SKU
is worse than a failed order.

What happens if capture is late:

| Case | Behaviour |
| :--- | :--- |
| Capture at 31 minutes | Reservation has expired; the order is re-checked and re-reserved if stock exists |
| Re-check fails | Order is cancelled with `NO_STOCK_AFTER_ORDER` |
| Provider webhook lost | A reconciliation job re-checks authorisations every 10 minutes |

## Why allocation needs the warehouse

A soft reservation that the warehouse never sees is just a number in our database. The transition
to `ALLOCATED` is the only point where we know a picker can actually reach the unit, which is why
the promise to the customer is not strengthened at `SOFT` but the stock is still protected.

## Enforcement

The state machine is enforced by the reservation worker; no other component may write a reservation
row. API callers can request a reservation and a release, and can read a reservation, but they
cannot set a state directly. That rule exists because two teams asked for "just a small override"
during discovery, and both would have created a path to oversell.

## Related

[Reservation rules](./reservation-rules.md) · [Reservation events](../specification/reservation-events.md) ·
[ATP service](../../architecture/services/atp-service.md)
