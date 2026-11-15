# Test Cases — Delivery Date Scenarios

Status: Draft · Owner: Aisha Bello · Last updated: 2026-11-13

The date calculation has more edge cases than anything else in the programme, because it combines
warehouse, cut-off, carrier, postcode and calendar. These cases are the ones that have produced real
wrong promises, either in the baseline measurement or in UAT rehearsals.

## The cases

| ID | Given | When | Then |
| :--- | :--- | :--- | :--- |
| DD-01 | Midlands, stock, 11:00 Monday | Quote requested | Next working day (Tuesday) |
| DD-02 | Midlands, 12:31 Monday | Quote requested | Wednesday, not Tuesday (AC-10) |
| DD-03 | Midlands, 14:59 Monday | Quote requested | Wednesday |
| DD-04 | Glasgow, 12:30 Monday | Quote requested | Wednesday (14:30 carrier, 12:00 promise) |
| DD-05 | Friday 16:00 | Quote requested | Tuesday, not Saturday |
| DD-06 | Holiday Monday, order Sunday | Quote requested | Wednesday, buffer applied (AC-11) |
| DD-07 | 2027-12-23, next-day selected | Quote requested | No next-day promise; two-day only |
| DD-08 | Scottish island postcode | Quote requested | Two-day, surcharge shown |
| DD-09 | Bulky, slot available Friday | Quote requested | Friday, range of days |
| DD-10 | Bulky, 15 days out | Quote requested | Week commencing, not a day (AC-12) |
| DD-11 | Locker and next-day both available | Quote requested | Both offered, locker is earlier |
| DD-12 | Basket 3 lines, 2 warehouses | Quote requested | Two groups, headline is the later date |
| DD-13 | One line out of stock | Quote requested | No date for that line; others unchanged |
| DD-14 | Postcode with no parcel service | Quote requested | No date, collection offered |
| DD-15 | Bank holiday in the middle of lead time | Quote requested | Skip the day, no extra buffer (AC-11) |
| DD-16 | Order at 23:50 Friday | Quote requested | Tuesday, accounting for the morning shift |

## The ones that catch real bugs

**DD-02** is the 12:30 cut-off. It is easy to implement against 15:00 because that is the carrier
contract, and the consequence is a 2.5-hour band of wrong promises.

**DD-06 vs DD-15** look contradictory and are not: the buffer applies to orders placed in a bank
holiday week, not to lead-time arithmetic. Testing one without the other lets a bug hide in the
difference.

**DD-16** catches timezone and overnight-shift errors. An order at 23:50 is promised from the next
morning's capacity, not from the day it was placed.

## Calendar fixtures

| Fixture | Dates | Used by |
| :--- | :--- | :--- |
| `calendar-2027` | Full year with regional holidays | All |
| `calendar-peak` | Peak cut-offs applied | DD-07 |
| `calendar-scotland` | Scottish holidays included | DD-08 |

The calendar fixtures are the runtime configuration, not a copy, so a test failure means a real
configuration difference rather than a stale test file.

## Expected-date table

| Ordered (UK time) | Warehouse | Service | Promised |
| :--- | :--- | :--- | :--- |
| Mon 11:00 | Midlands | Next day | Tue |
| Mon 12:31 | Midlands | Next day | Wed |
| Mon 13:00 | Glasgow | Next day | Wed |
| Fri 12:00 | Midlands | Next day | Mon |
| Fri 12:31 | Midlands | Next day | Tue |
| Sat 10:00 | Midlands | Next day | Tue |
| Sun 10:00 | Midlands | Next day | Tue |
| Mon 11:00 | Northgate | Two day | Wed |
| Mon 11:00 | Riverside | Two person | Fri–Tue |

## Related

[Delivery date logic](../../delivery-promise/calculation/delivery-date-logic.md) ·
[Cut-off times](../../delivery-promise/calculation/cut-off-times.md) ·
[Unavailable dates](../../delivery-promise/calculation/unavailable-dates.md)
