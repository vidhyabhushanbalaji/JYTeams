# Reservation Policy

Status: In review · Owner: Sofia Mendes · Last updated: 2026-11-13

When stock becomes unavailable to other customers, for how long, and what happens when the order
never happens. This is the workstream that decides the business rules; the services only implement
them.

## The answer in one paragraph

Stock is **soft-reserved when payment is authorised**, for 30 minutes, refreshed by the payment
provider's confirmation webhook. A soft reservation reduces availability everywhere it is shown but
does not commit a warehouse. It becomes a **hard allocation when the warehouse builds a pick wave**
and accepts it. Reservations are released on cancellation, payment failure or expiry, always with a
reason code. Pre-orders reserve at their release date, and collection reserves store stock for 5
days from the moment the store confirms the pick.

## Where each part lives

| Question | Document |
| :--- | :--- |
| How does a reservation move between states? | [Reservation lifecycle](./policy/reservation-lifecycle.md) |
| What are the actual rules, by ID? | [Reservation rules](./policy/reservation-rules.md) |
| What stops an oversell? | [Oversell prevention](./policy/oversell-prevention.md) |
| Pre-orders and backorders | [Pre-orders](./policy/pre-orders-and-backorders.md) |
| Cancellations and releases | [Cancellations](./policy/cancellations-and-releases.md) |
| Split shipments, partial availability, returns | [Edge cases](./edge-cases/) |
| What the ATP service must implement | [ATP service contract](./specification/atp-service-contract.md) |
| Why we chose this timing | [Reservation timing options](./specification/reservation-timing-options.md) |

## Status of the rules

| State | Count | Note |
| :--- | :--- | :--- |
| Agreed, in the rule table | 18 | Each has an owner and a test case |
| Open | 2 | RSV-06 bulky items, RSV-11 collection expiry |
| Out of scope this release | 6 | Wholesale allocation, promotions, returns |
| **Tracked in total** | **26** | The rule table plus the out-of-scope list |

M2 is signed off when the open count is zero and every rule has a test in
[customer testing](../customer-testing/strategy/acceptance-criteria.md).

## The two open rules

| Rule | Question | Options | Decision by |
| :--- | :--- | :--- | :--- |
| RSV-06 | Reserve bulky items at order, or at carrier booking? | Reserve early (protects the customer, ties up stock for up to 5 days) or reserve at booking (protects stock, risks a failed booking) | Steering, 2026-12-03 |
| RSV-11 | How long can a collection reservation hold store stock? | 3 days (tight, more cancellations) or 5 days (current store practice) | Sofia Mendes, 2026-11-27 |

## Principles the rules follow

1. A reservation is a promise to a customer, so it may only be released when that promise is broken.
2. Every release carries a reason code, because warehouses need to know why stock reappeared.
3. If the system cannot tell whether stock is current, it must behave conservatively.
4. A rule that cannot be explained to a store colleague in one sentence is too complicated.

## Related

[ATP service contract](./specification/atp-service-contract.md) · [Policy workshop](./specification/workshop-2026-10-16.md) ·
[ADR 0001](../decisions/0001-reserve-stock-at-payment-authorisation.md)
