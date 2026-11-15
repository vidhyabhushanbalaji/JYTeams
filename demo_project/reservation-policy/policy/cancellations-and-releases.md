# Cancellations and Releases

Status: Agreed · Owner: Tom Alder · Last updated: 2026-11-06

A cancellation is the customer's decision; an expiry is ours. Both end a reservation, and both look
identical to a warehouse unless the reason is carried with the release. This document is about the
end of the reservation, not the refund.

## Who can cancel, and when

| Actor | Window | Effect on reservation |
| :--- | :--- | :--- |
| Customer, before dispatch | Anytime (consumer right) | Release with `CUSTOMER_CANCELLED` |
| Customer, after dispatch | Returns process | Reservation already `DISPATCHED`; stock returns via restock |
| Contact centre agent | Anytime before dispatch | Release with `CUSTOMER_CANCELLED` |
| Marketplace buyer | 1 hour on eBay, 30 min on Amazon | Release with `CUSTOMER_CANCELLED` if before allocation |
| Warehouse | Anytime, with a reason | Release with `WAREHOUSE_REJECTED` |
| Payment provider | Authorisation reversal | Release with `PAYMENT_FAILED` |

## The three endings that matter

### Cancellation before allocation

Simple: the reservation is released, stock is available again within two seconds, and the
storefront sees it on the next availability read. The warehouse never knew the unit was claimed, so
there is nothing to tell it.

### Cancellation after allocation

Harder. The unit is on a pick list in a warehouse. The release sets the reservation to `RELEASED`
and emits a `reservation.released` event, which the integration hub forwards to the warehouse. The
warehouse confirms within one poll cycle. Until then, the unit is shown as available but physically
promised, which is an accepted two-cycle exposure.

### Expiry

An expiry is a release we chose, not one the customer asked for. It happens when capture does not
complete in 30 minutes (60 after RSV-02), or when a collection hold runs out under RSV-11.

Expiry runs as a scheduled job every 60 seconds, deliberately offset by 10 seconds from the wave
allocation window so that a reservation is never released in the same second a warehouse tries to
allocate it. That offset came out of a UAT rehearsal where seven units were double-claimed in a
single second.

## Release propagation

| Consumer | How it learns | Delay |
| :--- | :--- | :--- |
| Storefront | Reads availability live | Next request |
| Marketplaces | Inventory push | Up to 5 min |
| Warehouse | `reservation.released` event or next feed poll | 2 s to 15 min |
| Customer | Email or account page | CR-009 pending |

The customer is the slowest to find out, which is the reasoning behind CR-009 (notify when the
promise changes) and the reason the contact centre treats a date change as a call driver.

## Reason codes and reporting

Every release carries one of the eight codes in
[reservation rules](./reservation-rules.md). The daily operations report groups them:

| Group | Codes | What it tells us |
| :--- | :--- | :--- |
| Customer choice | `CUSTOMER_CANCELLED`, `NOT_COLLECTED` | Demand changed, not a system failure |
| Payment | `PAYMENT_FAILED`, `RESERVATION_EXPIRED` | Checkout friction |
| Stock reality | `WAREHOUSE_REJECTED`, `STOCK_CORRECTION` | Data quality |
| Policy | `SKU_DISCONTINUED`, `MANUAL_OVERRIDE` | Process exceptions, reviewed weekly |

A rising "stock reality" group is the earliest warning that a feed is drifting, which is why it is
on the operations dashboard rather than buried in a weekly report.

## Related

[Lifecycle](./reservation-lifecycle.md) · [Reservation events](../specification/reservation-events.md) ·
[Oversell prevention](./oversell-prevention.md)
