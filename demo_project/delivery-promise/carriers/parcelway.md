# Parcelway

Status: Agreed · Owner: Gavin Shore · Last updated: 2026-11-06

Parcelway carries 78 % of our parcels: next-day and two-day, 96 % of UK postcodes, Saturday delivery
on the next-day service. It is the carrier the promise is built on for anything that is not bulky.

## Service summary

| Service | Lead time | Cut-off | Days | Share |
| :--- | :--- | :--- | :--- | :--- |
| Next-day | Next working day | 15:00 | Mon–Fri | 61 % |
| Next-day Saturday | Saturday | 15:00 Friday | Sat | 9 % |
| Two-day | 2 working days | 15:00 | Mon–Fri | 26 % |
| Economy | 3–5 working days | 15:00 | Mon–Fri | 4 % |

## Integration

| Capability | Endpoint | Notes |
| :--- | :--- | :--- |
| Serviceability by postcode | `GET /v2/serviceability` | Returns services, lead times, restrictions |
| Quote | `POST /v2/rates` | Price and service per parcel |
| Book | `POST /v2/consignments` | Returns consignment and tracking number |
| Track | `GET /v2/tracking/{id}` | Webhook preferred |
| Label | `GET /v2/labels/{id}` | PDF, 4×6 |
| Cancel | `DELETE /v2/consignments/{id}` | Until collection scan |

Sandbox is live and usable for UAT. Rate limit is 600 calls per minute per account, which is enough
for peak at 30 bookings per second with headroom.

## Serviceability rules that matter

| Rule | Detail |
| :--- | :--- |
| Postcode coverage | 96.1 % of UK postcodes; the gaps are Scottish islands, parts of the Highlands and one BT postcode block |
| Offshore surcharge | `HS1`, `ZE`, `KW15-17`, `PA20-49` carry a surcharge and a two-day lead time |
| Maximum weight | 30 kg per parcel; above that, Northline |
| Maximum dimensions | 1.2 m length; garden furniture is always Northline |
| Saturday | Available on next-day only, and not to 41 postcodes |
| Age verification | Not supported; alcohol and sharp items are excluded from the category list |

The 41 Saturday-excluded postcodes are the single most common cause of a wrong Saturday promise in
the old system, because the old rules only checked the service, not the postcode.

## Operating rhythm

| Time | Event |
| :--- | :--- |
| 12:30 | Last booking accepted for the 15:00 collection at Midlands |
| 14:30 | Glasgow collection, 14:30 cut-off |
| 15:00 | Collection from Midlands and Northgate |
| 19:00 | First tracking events |
| 23:00 | Serviceability refresh from Parcelway |

## Performance

| Measure | Last 90 days | Target |
| :--- | :--- | :--- |
| On-time delivery | 96.8 % | 96 % |
| Next-day success | 97.9 % | 97 % |
| Damage rate | 0.14 % | ≤ 0.2 % |
| Lost parcels | 0.05 % | ≤ 0.1 % |
| Average cost per parcel | £3.86 | — |

## Known constraints

- No Sunday or bank holiday collection, which the calendar already reflects.
- Serviceability data refreshes once a day, so a newly restricted postcode is discovered a day late.
- The API returns serviceability but not capacity: on a heavy day Parcelway can decline a booking,
  and the promise has no way to know that in advance. Capacity risk is tracked in the carrier review.

## Related

[Service levels](../calculation/service-levels.md) · [Carrier performance](./carrier-performance.md) ·
[Delivery date logic](../calculation/delivery-date-logic.md)
