# Peak and Holiday Calendar

Status: Agreed · Owner: Gavin Shore · Last updated: 2026-11-13

Which days are not working days, which days are busy, and what the promise does about each. This is
the 2027 calendar as it stands; the calendar service is the authoritative copy at runtime.

## 2027 closures

| Date | Day | What | Effect on promise |
| :--- | :--- | :--- | :--- |
| 2027-01-01 | Friday | New Year's Day | No collections, no delivery |
| 2027-03-26 | Friday | Good Friday | No collections, no delivery |
| 2027-03-29 | Monday | Easter Monday | No collections, no delivery |
| 2027-05-03 | Monday | Early May bank holiday | No collections, +6 h buffer |
| 2027-05-31 | Monday | Spring bank holiday | No collections, +6 h buffer |
| 2027-08-30 | Monday | Summer bank holiday | No collections, +6 h buffer |
| 2027-12-24 | Friday | Christmas Eve | No next-day promise after 12:00 |
| 2027-12-25–26 | Sat–Sun | Christmas | No delivery |
| 2027-12-27–28 | Mon–Tue | Substitute days | Two-day service only |
| 2028-01-01 | Saturday | New Year's Day | No delivery |

Scotland has an additional holiday on 2027-01-04 and 2027-11-30, which affects Glasgow DC and
Scottish deliveries. The calendar service holds holidays per region, not per country.

## Peak

| Period | Dates | Orders vs baseline | Promise handling |
| :--- | :--- | :--- | :--- |
| Black Friday week | 2027-11-22 to 2027-11-30 | 3.7× | Cut-offs move earlier; next-day capped |
| Pre-Christmas | 2027-12-01 to 2027-12-20 | 2.1× | Two-day service becomes the default |
| Boxing Day sale | 2027-12-26 to 2028-01-05 | 1.6× | Two-day only until 2027-12-29 |
| January sale | 2028-01-06 to 2028-01-20 | 1.3× | Normal after 2028-01-08 |

Peak is after the May launch, which is the main reason the launch date was moved from March: a
launch that ends three months before peak is a launch with time to fix its own problems.

## Cut-off changes

| Period | Midlands | Glasgow | Northgate | Riverside |
| :--- | :--- | :--- | :--- | :--- |
| Normal | 12:30 | 12:00 | 12:00 | 11:00 |
| Peak | 11:00 | 10:30 | 10:30 | 09:30 |
| Christmas week | 11:00 | 11:00 | 11:00 | No bulky promise |

These are configured, not coded, and they are changed by Gavin Shore through the admin screen two
weeks before the period begins.

## Carrier capacity

| Event | Carrier constraint | Promise response |
| :--- | :--- | :--- |
| Black Friday | Parcelway caps at 14,000 parcels/day | Next-day withdrawn when the cap is 90 % used |
| Christmas | Northline stops named-day from 2027-12-15 | Named day withdrawn; standard only |
| Easter | Northline Scotland at 88 % utilisation | Bulky Scotland promised 5–7 days, not 3–5 |
| Royal events | Ad hoc closures | Handled as a bank holiday, added by the calendar owner |

The Parcelway cap is the one that needs a live feed: the promise service reads a daily capacity
figure published by Parcelway at 06:00 and withdraws next-day for the day if the cap is nearly
reached. That feed is not in the May scope; the manual equivalent is a hold that Marcus can apply.

## Maintaining the calendar

| Who | What | When |
| :--- | :--- | :--- |
| Gavin Shore | Confirms the next year's calendar | Each October |
| Nadia Kerr | Loads it into the calendar service | Each November |
| Marcus Feld | Adds ad hoc closures with a reason | As needed |

The calendar service refuses a date with no reason, so every closure is explainable later. That rule
came from a 2026 incident where a delivery date was wrong for a week because of an unrecorded
one-day closure at a depot.

## Related

[Delivery date logic](./delivery-date-logic.md) · [Cut-off times](./cut-off-times.md) ·
[Change freeze](../../launch-readiness/cutover/change-freeze.md)
