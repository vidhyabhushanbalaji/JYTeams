# Northline Freight

Status: Agreed · Owner: Gavin Shore · Last updated: 2026-11-06

Northline delivers everything Parcelway cannot: furniture, garden structures, anything over 30 kg or
1.2 m. Two-person delivery to a room of choice, booked into a slot, with a 3–5 working day lead
time. It is 6 % of orders and the source of most delivery complaints, because the promise and the
booking are not the same thing.

## Service summary

| Service | Lead time | Days | Notes |
| :--- | :--- | :--- | :--- |
| Standard two-person | 3–5 working days | Mon–Sat | Slot chosen by carrier |
| Named day | 3–7 working days | Mon–Sat | Customer chooses from available slots |
| Room of choice | +1 day | Mon–Fri | Two flights of stairs maximum |
| Assembly | +2 days | Mon–Fri | Selected products only |

## The booking problem

A bulky order needs a **run slot**, and slots are finite. The current process books the delivery
after the warehouse allocates the item, which can be three days after the order. If no slot exists
inside the promised window, the customer is called and rebooked, at a cost of **£46 per rebooking**.

| Metric | Value |
| :--- | :--- |
| Bulky orders per day | 410 |
| Rebookings per day | 96 |
| Rebooking cost per day | £4,416 |
| Promise met for bulky | 58 % |
| Average days from order to delivery | 6.4 |

That 58 % is the worst segment in the business and the reason bulky items sit at the centre of two
open decisions (RSV-06, and the slot-aware promise in this document's related links).

## Capacity

| Region | Runs per day | Utilisation | Constraint |
| :--- | :--- | :--- | :--- |
| Midlands and South | 34 | 81 % | Driver shortage in December |
| North and Scotland | 19 | 88 % | At capacity; no additional runs before Q3 2027 |
| Wales and South West | 11 | 64 % | Headroom |

The North and Scotland figure is R-06: at 88 % utilisation, Easter week 2027 will not have capacity
for a launch promotion, and the promise cannot see that. Northline has offered a capacity
commitment for weeks 15–18 at a fixed rate, which Gavin is pricing.

## Integration

| Capability | Endpoint | Notes |
| :--- | :--- | :--- |
| Serviceability and zones | `GET /zones/{postcode}` | Weekly zone file, not real time |
| Slot availability | `GET /slots?postcode&from&to` | Returns bookable slots, 14-day horizon |
| Book | `POST /bookings` | Requires a slot ID |
| Rebook | `PATCH /bookings/{id}` | Allowed up to 24 hours before |
| Capacity forecast | Weekly CSV | Runs and utilisation per region |

The 14-day slot horizon is a hard limit: we cannot promise a bulky delivery beyond 14 days, which is
why bulky promises show a week rather than a day beyond day 10.

## Why the lead time is 3–5 days, not 2

Two days of transit and one to three days of slot availability. The variance is capacity, not
distance. The calculation uses the **worst** case plus a buffer, which is why bulky promises are
conservative even when a slot exists tomorrow.

## Performance

| Measure | Last 90 days | Target |
| :--- | :--- | :--- |
| On-time within slot | 91.2 % | 93 % |
| Damage rate | 1.6 % | ≤ 1.2 % |
| Failed access (nobody home) | 4.1 % | ≤ 3 % |
| Assembly completion | 99.4 % | 99 % |

Damage is the highest in the network, and almost all of it is furniture edges in transit without
corner protection. A packaging change is being trialled at Riverside.

## Related

[Riverside Logistics](../../stock-feeds/warehouses/riverside-logistics.md) ·
[Peak and holiday calendar](../calculation/peak-and-holiday-calendar.md) ·
[Carrier performance](./carrier-performance.md)
