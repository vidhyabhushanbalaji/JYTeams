# Cut-off Times

Status: Agreed · Owner: Gavin Shore · Last updated: 2026-11-06

Two different cut-offs exist for every warehouse and they are constantly confused: the **promise
cut-off**, after which we stop claiming today, and the **carrier cut-off**, after which the carrier
will not collect. The gap between them is the warehouse's working time.

## The table

| Warehouse | Last wave built | Promise cut-off | Carrier cut-off | Gap |
| :--- | :--- | :--- | :--- | :--- |
| Midlands DC | 12:30 | 12:30 | 15:00 | 2 h 30 |
| Glasgow DC | 12:00 | 12:00 | 14:30 | 2 h 30 |
| Northgate Fulfilment | 12:00 | 12:00 | 14:00 | 2 h |
| Riverside Logistics | 11:00 | 11:00 | 13:00 | 2 h |
| Stores (collection) | — | Closing minus 1 h | — | — |

## Why we promise on the earlier number

A promise is a commitment about the parcel, not about the paperwork. An order accepted at 14:00 is
booked with the carrier, but it is not in a wave, so it will sit until the next day's 12:30 wave.
Promising next-day would be wrong for every order between 12:30 and 15:00, which is **11 % of orders**
and was the largest single source of promise misses in the baseline.

The old system used 15:00 because that is what the carrier contract says, which is a good example of
a technically correct answer that is operationally wrong.

## What happens after the cut-off

| Time | Behaviour |
| :--- | :--- |
| After promise cut-off, before carrier cut-off | Order accepted, promised for the next working day |
| After carrier cut-off | Order accepted, promised for the next working day, no carrier booking until morning |
| After 22:00 | Same as above; overnight promises account for the morning shift |

The site does not stop selling after cut-off. It stops promising today, which is a different thing
and a deliberately chosen one: turning off next-day after 12:30 would cost about 4 % of orders.

## Holiday cut-offs

| Date | Effect |
| :--- | :--- |
| Day before a bank holiday | Promise cut-off unchanged; carrier cut-off moves 2 hours earlier |
| Christmas Eve | No next-day promise; two-day only |
| Between Christmas and New Year | Two-day service only, no Saturday |
| New Year's Day | No collections |
| Easter Saturday | No bulky delivery; parcels unaffected |

The calendar service holds these dates, and the delivery-date logic reads the effective cut-off from
it rather than from a table in code.

## Changing a cut-off

A cut-off change needs both Gavin Shore and the warehouse's operations lead, and it is tested against
the date calculation suite before it is deployed. It is a business rule with a technical
implementation, not the other way round.

| Change | Lead time | Example |
| :--- | :--- | :--- |
| Seasonal cut-off (peak) | 4 weeks | Midlands to 11:00 from 20 November |
| Permanent change | 6 weeks | A new wave time |
| Emergency (site failure) | Immediate, logged | Carrier collection cancelled |

## Related

[Delivery date logic](./delivery-date-logic.md) · [Peak and holiday calendar](./peak-and-holiday-calendar.md) ·
[Parcelway](../carriers/parcelway.md)
