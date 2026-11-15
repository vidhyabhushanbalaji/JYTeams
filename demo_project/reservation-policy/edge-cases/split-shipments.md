# Split Shipments

Status: Agreed · Owner: Sofia Mendes · Last updated: 2026-11-06

38 % of orders leave in more than one parcel, and today the customer discovers that at dispatch. The
reservation policy cannot make splits disappear, but it can make them predictable, which is the
difference between a promise and an apology.

## Why orders split

| Cause | Share of splits | Could we avoid it? |
| :--- | :--- | :--- |
| Items stocked in different warehouses | 61 % | Only by transferring stock, which costs more than it saves |
| One item bulky, one small | 14 % | No: different carriers and different vans |
| One item personalised | 6 % | No: made in Glasgow |
| Stock short in the chosen warehouse | 11 % | Partly, with better availability data |
| Deliberate consolidation failure | 8 % | Yes: routing splits before it checks stock |

## The rule

A split is decided by availability, not by routing. When the order is reserved, the reservation
worker asks for availability per line and groups the lines by the warehouse that can serve them.
Each group becomes a shipment with its own reservation, its own promise and its own tracking.

| Rule | Detail |
| :--- | :--- |
| Maximum shipments per order | 3 (a fourth group is consolidated back into the smallest) |
| Reservation per shipment | Independent; cancelling one does not release the other |
| Promise per shipment | Each has its own date; the order's headline date is the latest |
| Customer messaging | The confirmation names each shipment and its date |
| Delivery cost | Charged once, as today |

## What the customer sees

| Moment | Today | Under Truestock |
| :--- | :--- | :--- |
| Confirmation | "We will email you" | "Parcel 1 of 2, Tue 25 May. Parcel 2 of 2, Wed 26 May." |
| Dispatch | Two emails arrive separately | Each email references the shipment |
| Delay on one shipment | No notification | Date change notification (CR-009) |

## The awkward case

A bulky item and a small item in the same order: the bulky item has a five-day lead time and the
small one can arrive tomorrow. We show one order, two dates, and the customer often asks why the
small item is waiting. It is not waiting; it is just in the same order record. The messaging rule
is to name the parcels, not the order, and the customer testing plan includes a case for exactly
this confusion.

## What we are not doing

Combining shipments in a later wave to save carriage. Fulfilment evaluated it in 2025 and found it
added 1.4 days to the average delivery, which the promise cannot afford. It stays a post-peak
candidate.

## Related

[Partial availability](../edge-cases/partial-availability.md) · [Reservation rules](../policy/reservation-rules.md) ·
[Delivery date logic](../../delivery-promise/calculation/delivery-date-logic.md)
