# Pre-Orders and Backorders

Status: Agreed · Owner: Tom Alder · Last updated: 2026-11-06

Two ways of selling stock that does not exist yet. Both are small in volume and both are where a
reservation policy is most likely to create a customer complaint, because the customer has already
given us money.

## Pre-orders

A pre-order is a product sold before its release date, with a date we publish. In 2026 that is
**38 launch products**, mostly garden furniture in February and Christmas gifting in October.

| Rule | Behaviour | Rationale |
| :--- | :--- | :--- |
| Payment | Taken at order | The customer's place in the queue is the thing they are buying |
| Reservation | None until the release date | Stock does not exist in a feed; reserving would be fiction |
| At release date minus 7 days | Reservation attempted for every pre-order, oldest first | Gives a week to resolve shortfalls before dispatch |
| Shortfall | Customer offered a revised date or a refund, in that order | Refunds are the last resort, not the first |
| Cancellation before release | Full refund, no fee | Required by consumer regulation |
| Allocation order | Order date, then payment time | Never by value or by channel |

The seven-day window is the number Sofia and Tom argued over: three days was too tight to re-plan a
container, fourteen days tied up too much stock. Seven matches the freight forwarder's notice
period.

## Backorders

A backorder is a line we accepted against expected stock, mostly in wholesale. Consumer backorders
are only created in one case: partial availability on a multi-line order (RSV-20), where the
customer chose to wait rather than split.

| Rule | Consumer | Wholesale |
| :--- | :--- | :--- |
| Reservation | Reserved when stock arrives, in order date order | Allocated by the desk, in importance order |
| Customer communication | Date range, updated when the date changes | Email from the desk |
| Cancellation | Anytime before dispatch | Per contract terms |
| Maximum wait | 28 days, then automatic cancellation with refund | No limit |
| Priority against new orders | Backorders before new orders for the same SKU | Same |

## Why consumer backorders are limited

The contact centre asked for broad backorders to save sales. Trading refused, for a good reason:
a backordered consumer order holds a promise with no stock behind it, which is exactly the failure
the programme exists to remove. The 28-day cap exists so a backorder cannot quietly become a
permanent liability on the ledger.

## Interaction with the promise

A pre-order shows the release date, not a delivery estimate. A backorder shows "from 12 March",
never a firm date. Both are the only places where the site shows something other than a promised
delivery date, and both are exceptions the customer messaging rules allow
([product page messaging](../../delivery-promise/customer-messaging/product-page-messaging.md)).

## Related

[Reservation rules](./reservation-rules.md) · [Partial availability](../edge-cases/partial-availability.md) ·
[Product page messaging](../../delivery-promise/customer-messaging/product-page-messaging.md)
