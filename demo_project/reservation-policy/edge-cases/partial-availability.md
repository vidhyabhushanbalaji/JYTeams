# Partial Availability

Status: Agreed · Owner: Tom Alder · Last updated: 2026-11-06

The customer ordered four, we have two. Today the order is cancelled entirely, or the line is
fulfilled short and someone emails. Neither is acceptable when the customer is standing at checkout
with a promise on screen.

## The rule (RSV-20)

Availability is evaluated per line. If a line cannot be fully satisfied, three options exist in a
fixed order of preference:

| Preference | Behaviour | When it applies |
| :--- | :--- | :--- |
| 1 | Fulfil what exists from another warehouse | Another warehouse has the full quantity |
| 2 | Fulfil what exists, backorder the rest | The shortfall is ≤ 28 days away |
| 3 | Reduce the line and tell the customer | No restock date, or the customer chose it |

At checkout the customer is shown the choice only when the reduction is more than one unit; a single
unit shortfall is absorbed silently, because asking "would you like 2 instead of 3?" at the payment
step loses more orders than it saves.

## What the API returns

`POST /availability/quote` with lines returns one of three shapes per line:

```json
{ "line": 2, "requested": 3, "available": 2, "shape": "partial",
  "options": ["reduce", "backorder"], "backorder_from": "2027-06-02" }
```

| Shape | Meaning |
| :--- | :--- |
| `full` | The requested quantity is available |
| `partial` | Some is available, with options |
| `none` | Nothing is available; backorder or refuse |

The shape is part of the contract, not an implementation detail: the storefront renders different
copy for each, and the reservation worker behaves differently.

## Worked examples

| Scenario | Stock | Result |
| :--- | :--- | :--- |
| 3 requested, Midlands has 5 | 5 | `full`, reserve 3 at Midlands |
| 3 requested, Midlands has 1, Glasgow has 4 | 5 | `full`, reserve 3 at Glasgow (rule 1) |
| 3 requested, 2 in total, restock 9 June | 2 | `partial`, options reduce or backorder |
| 3 requested, 0 available, no restock date | 0 | `none`, backorder not offered |
| 3 requested, store collection chosen | store has 2 | `partial`, reduce only: no backorder to a store |

## Why not reserve optimistically

A tempting alternative is to reserve what exists and let the rest resolve later. Fulfilment rejected
it because it creates a reservation the warehouse cannot satisfy, which is precisely the phantom
stock behaviour that produces the contact-centre calls.

## Effect on the promise

A partial line with a backorder produces two promises: one for the shipment that exists and one
"from" date for the backorder. The order's headline date is the later of the two, and the customer
sees both.

## Related

[Pre-orders and backorders](../policy/pre-orders-and-backorders.md) · [Split shipments](./split-shipments.md) ·
[Availability API](../../reference/api/availability-api.md)
