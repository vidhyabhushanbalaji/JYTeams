# Delivery Date Logic

Status: Draft · Owner: Nadia Kerr · Last updated: 2026-11-13

The algorithm, in order, with the edge rules that took the longest to agree. Every channel uses this
one calculation; a marketplace date and a website date for the same SKU must be the same date.

## Inputs

| Input | Source | If missing |
| :--- | :--- | :--- |
| Eligible warehouses and availability | ATP | No date; fallback |
| Serviceability and services | Carrier API | No date for that postcode |
| Cut-off for warehouse and service | Configuration | No date; alert |
| Business calendar | Calendar service | No date; alert |
| Product restrictions | Atlas | No postcode date; collection offered |
| Buffer for bank holidays | Policy | Applied by default |

## The calculation

1. **Choose the warehouse.** The nearest eligible warehouse with availability, using the carrier's
   serviceability rather than the static postcode table.
2. **Choose the service.** The fastest service serviceable at the postcode that the parcel's size and
   weight allow.
3. **Apply the cut-off.** If the order time is after the warehouse's cut-off for that service, move
   to the next working day.
4. **Add the lead time.** Working days only, per the carrier's service table.
5. **Exclude non-delivery days.** Sundays and bank holidays, from the calendar.
6. **Check the slot horizon.** Bulky: if the date is beyond the 14-day booking horizon, show a week
   instead of a day.
7. **Add the buffer.** 6 hours for bank holiday weeks (RSV-19), applied before rounding.
8. **Round to a day, in the customer's timezone.** Dates are shown as a day, never a timestamp.

## Worked examples

All times UK, orders placed on a Wednesday.

| Case | Order time | Warehouse | Cut-off | Service | Promised |
| :--- | :--- | :--- | :--- | :--- | :--- |
| Standard parcel, Midlands | 11:00 | Midlands | 15:00 | Next-day | Thursday |
| Standard parcel, after cut-off | 15:30 | Midlands | 15:00 | Next-day | Friday |
| Glasgow, after 14:30 | 15:00 | Glasgow | 14:30 | Next-day | Friday |
| Friday after cut-off | 16:00 | Midlands | 15:00 | Next-day | Monday |
| Before a bank holiday | Monday 10:00 | Midlands | 15:00 | Next-day | Wednesday |
| Bulky, slot available | 10:00 | Riverside | 13:00 | Two-person | Friday–Tuesday (range) |
| Bulky, beyond horizon | 10:00 | Riverside | 13:00 | Two-person | Week commencing 8 June |
| Locker | 13:00 | Midlands | 16:00 | Locker 24 h | Thursday |
| Store collection | 13:00 | Store | — | Collection | Ready Thursday |

The fifth row is the one people get wrong: the buffer is applied to the **promise**, not to the
working-day arithmetic, so the date moves out rather than the cut-off moving in.

## Why the cut-off is 12:30 for the promise, not 15:00

Midlands' carrier collection is 15:00, but its last wave is built at 12:30. An order accepted at
14:00 will be collected tomorrow, not today. The configuration therefore uses **12:30** as the
promise cut-off and 15:00 only as the carrier booking cut-off. The warehouse supervisor interview is
the source for this, and it is the single change that most improves promise accuracy for late orders.

| Warehouse | Promise cut-off | Carrier cut-off |
| :--- | :--- | :--- |
| Midlands DC | 12:30 | 15:00 |
| Glasgow DC | 12:00 | 14:30 |
| Northgate | 12:00 | 14:00 |
| Riverside | 11:00 | 13:00 |
| Stores | Store closing minus 1 hour | — |

## Multi-line orders

The order's headline date is the **latest** shipment date, because that is when the order is
complete. Each shipment shows its own date in the confirmation. For a basket where one line has no
date at all, the basket shows "some items have no confirmed date" rather than the latest date of the
rest, which would be misleading.

## Failure to compute

| Failure | Behaviour |
| :--- | :--- |
| Carrier API timeout | One retry, then fallback estimate |
| No serviceable service | No date; collection offered if possible |
| Stale stock | Fallback estimate |
| Calendar service down | Use the cached calendar; if older than 24 h, fail closed |
| Bulky without RSV-06 decided | Use the conservative option: reserve at order, promise 5 days |

"Fail closed" means no date. It is always preferable to a date we cannot defend, and it is the
reason the fallback copy exists.

## Related

[Cut-off times](./cut-off-times.md) · [Unavailable dates](./unavailable-dates.md) ·
[ADR 0010](../../decisions/0010-conservative-fallback-promise.md)
