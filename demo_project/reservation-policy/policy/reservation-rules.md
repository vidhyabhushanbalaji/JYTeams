# Reservation Rules

Status: In review · Owner: Sofia Mendes · Last updated: 2026-11-13

The rule table is the policy. If a behaviour is not in this table it is not agreed, and the
reservation worker must not implement it.

## Rules

| ID | Trigger | Effect | Expiry | Owner | State |
| :--- | :--- | :--- | :--- | :--- | :--- |
| RSV-01 | Payment authorised, consumer order | Reserve 1 unit per line at the nearest eligible warehouse | 30 min | Sofia Mendes | Agreed |
| RSV-02 | Payment capture confirmed | Extend the reservation to 60 min from authorisation | 60 min | Sofia Mendes | Agreed |
| RSV-03 | Warehouse accepts a wave | Soft becomes allocated; no expiry | None | Sofia Mendes | Agreed |
| RSV-04 | Order cancelled before allocation | Release all lines, reason `CUSTOMER_CANCELLED` | — | Tom Alder | Agreed |
| RSV-05 | Payment failure or capture timeout | Release all lines, reason `PAYMENT_FAILED` | — | Tom Alder | Agreed |
| RSV-06 | Bulky item order (two-person delivery) | Reserve at order or at carrier booking | 5 days | Sofia Mendes | **Open** |
| RSV-07 | Collection order, store confirmed the pick | Reserve store stock from the store's pool | 5 days | Elena Vasquez | Agreed |
| RSV-08 | Collection order, store has not picked in 24 h | Reminder task to the store, reservation stays | — | Elena Vasquez | Agreed |
| RSV-09 | Collection order collected | Reservation becomes `DISPATCHED` | — | Elena Vasquez | Agreed |
| RSV-10 | Collection order not collected | Release to store stock, reason `NOT_COLLECTED` | — | Elena Vasquez | Agreed |
| RSV-11 | Collection reservation length | 3 days or 5 days | — | Sofia Mendes | **Open** |
| RSV-12 | Stock feed older than its threshold | Do not reserve; return `ATP_STOCK_STALE` | — | Dan Whitcombe | Agreed |
| RSV-13 | Reservation against a warehouse in quarantine hold | Exclude units in quarantine from availability | — | Sofia Mendes | Agreed |
| RSV-14 | Order line for a discontinued SKU | Refuse the reservation, reason `SKU_DISCONTINUED` | — | Tom Alder | Agreed |
| RSV-15 | Pre-order line | No reservation until release date; then RSV-01 applies | — | Tom Alder | Agreed |
| RSV-16 | Wholesale order | No automatic reservation; reservation on desk confirmation | Manual | Ruth Iyer | Agreed |
| RSV-17 | Reservation release must carry a reason | Every release has one of the eight codes | — | Nadia Kerr | Agreed |
| RSV-18 | Manual hold switch engaged for a warehouse | No new reservations, existing ones kept | — | Marcus Feld | Agreed |
| RSV-19 | Bank holiday buffer | Add 6 hours to the promise window, not to the reservation | — | Tom Alder | Agreed |
| RSV-20 | Partial availability | Reserve what exists, split the line, mark the rest backordered | 30 min | Tom Alder | Agreed |

## Precedence

When two rules apply, the lower ID wins, except that RSV-12 (stale stock) and RSV-18 (manual hold)
always win because they are safety rules. This is deliberate: safety rules are not subject to
commercial negotiation at the point of sale.

## Release reason codes

| Code | Used when | Visible to warehouse |
| :--- | :--- | :--- |
| `CUSTOMER_CANCELLED` | Customer or agent cancelled | Yes |
| `PAYMENT_FAILED` | Authorisation failed, capture failed or timed out | Yes |
| `RESERVATION_EXPIRED` | 30/60 minutes elapsed | Yes |
| `NOT_COLLECTED` | Collection window passed | Yes |
| `WAREHOUSE_REJECTED` | Warehouse could not pick the line | Yes |
| `SKU_DISCONTINUED` | Product withdrawn mid-order | No |
| `STOCK_CORRECTION` | Feed showed the unit does not exist | No |
| `MANUAL_OVERRIDE` | Fulfilment team released it | Yes |

The two codes not visible to a warehouse are the ones where the warehouse never had the unit, so
telling it about the release would create confusion rather than clarity.

## How a rule gets changed

Write the change, get Sofia Mendes to agree, add a test case, update
[policy configuration](../specification/policy-configuration.md), and note it in the change log at
the bottom of that file. A rule changed after 2027-01-11 needs a change request.

## Related

[Lifecycle](./reservation-lifecycle.md) · [Oversell prevention](./oversell-prevention.md) ·
[Policy configuration](../specification/policy-configuration.md)
