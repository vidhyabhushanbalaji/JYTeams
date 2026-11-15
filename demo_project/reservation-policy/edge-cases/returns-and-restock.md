# Returns and Restock

Status: Agreed · Owner: Marcus Feld · Last updated: 2026-11-06

A return is the mirror of a reservation: stock comes back and becomes sellable again. The timing
matters more than the process, because a returned item that is available before it is physically
checked creates exactly the phantom stock the programme is trying to remove.

## The path of a returned item

| Step | Where | Effect on availability |
| :--- | :--- | :--- |
| Customer requests return | Online | None |
| Parcel arrives at returns centre | Midlands DC | None |
| Item received and graded | Returns desk | `QUARANTINE` if not resellable, otherwise pending |
| Item put away | Warehouse | Available at the next feed |
| Refund issued | Finance | None |

The gap between "received" and "available" is deliberate and currently 14 hours on average. The
target after launch is 4 hours for a same-day put-away.

## Grading

| Grade | Meaning | Sellable | Where it goes |
| :--- | :--- | :--- | :--- |
| A | Unopened, packaging intact | Yes | Back to stock, available immediately |
| B | Opened, complete | Yes, as "open box" | Back to stock as a separate SKU state |
| C | Incomplete or damaged packaging | No | Clearance channel |
| D | Faulty | No | Supplier return or write-off |

Only grade A and B affect the main stock figure. Grade B has its own availability pool, which is why
the availability service carries a `condition` dimension, not just a location.

## Rules

| Rule | Detail |
| :--- | :--- |
| Reservation | A returned item is not reserved; the original reservation ended at dispatch |
| Restock timing | Availability updated at put-away, never at receipt |
| Quarantine | Grade C and D are excluded from availability entirely (RSV-13) |
| Marketplace returns | Amazon returns arrive at Northgate; same grading, same rule |
| Store returns | Processed in store and reflected in the hourly store feed |
| Cross-channel | A website return to store does not become store stock until the store file runs |

## The known bad case

An item is returned, graded A, put away, and sold the same day. The picker then discovers the
customer kept the accessory. It happens about 40 times a month and is unfixable by policy: it is a
grading quality problem, so it is handled by spot checks rather than by the reservation system.

## What changes under Truestock

The reservation system does not touch returns directly, but two things improve: put-away events
from the warehouse systems feed availability within minutes rather than at the next snapshot, and
grade B stock gets its own explicit state instead of being mixed into the main number. That second
change is small and unexpectedly valuable: merchandising has wanted a separate open-box figure since
2024.

## Related

[Damaged and quarantine stock](./damaged-and-quarantine-stock.md) · [Warehouse systems](../../current-state/systems/warehouse-systems.md) ·
[Oversell prevention](../policy/oversell-prevention.md)
