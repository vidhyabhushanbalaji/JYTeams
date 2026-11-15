# Riverside Logistics

Status: Draft · Owner: Dan Whitcombe · Last updated: 2026-11-13

Riverside handles every bulky item we sell: 61,000 records, 1,200 oversized SKUs, two-person
delivery. It has the cleanest stock data of the five sources and the slowest feed, which is why it
is the one warehouse allowed a 45-minute staleness threshold.

## Feed properties

| Property | Today | Contract target |
| :--- | :--- | :--- |
| Mechanism | LogiCore delta API | Same |
| Paging | 2,000 records per page | 2,000 |
| Delta cadence | 15 minutes | 10 minutes |
| Full snapshot | On request, 11 minutes to generate | Nightly at 01:00 |
| Records | 61,000 | 61,000 |
| Stale threshold | 45 minutes | 45 minutes |

## The stock model

| Field | Meaning | Availability treatment |
| :--- | :--- | :--- |
| `available` | Sellable now | Included |
| `allocated` | Booked to a delivery run | Excluded |
| `quarantine` | Damage or quality hold | Excluded, correctly, today |
| `in_transit` | Between Riverside and a customer | Excluded |
| `customer_hold` | Customer asked to delay | Excluded |

Riverside is the only source that already applies quarantine correctly, which is why
[the quarantine rule](../../reservation-policy/edge-cases/damaged-and-quarantine-stock.md) cites it
as the model the other four are being brought up to.

## The 412 SKU problem (ISSUE-018)

412 bulky SKUs in Riverside's catalogue have no matching product in Atlas. They are old furniture
lines still sellable through Riverside but no longer merchandised, plus 38 SKUs where Atlas has two
products and Riverside has one.

| Consequence | Detail |
| :--- | :--- |
| Promise unavailable | The 412 SKUs get no delivery date |
| Availability leak | They appear in the feed but cannot be quoted |
| Owner | Ben Osei, due 2026-12-04 |

The interim fix is a mapping table maintained by buying. It is explicitly temporary: a mapping
table becomes a permanent lie if nobody owns it, so it has an owner, a review date and a deletion
date of 2027-03-31.

## Why the feed is slow

LogiCore generates each delta by walking its own allocation tables, which lock during a delivery run
between 11:00 and 13:00. A delta requested then takes 90–140 seconds instead of 4. Riverside has
offered a 10-minute cadence outside those hours and a 20-minute cadence inside them, which is the
contract being negotiated now.

## Delivery booking

Riverside is the warehouse that exposes the bulky-item policy problem: a two-person delivery has to
be booked onto a run, and a run has capacity. Reserving at order means the unit is held while the
booking may fail; reserving at booking means the customer may be told yes and then wait. The
numbers behind that decision are in
[reservation timing options](../../reservation-policy/specification/reservation-timing-options.md)
and the decision is blocked on RSV-06.

## Related

[Northgate Fulfilment](./northgate-fulfilment.md) · [Northline Freight](../../delivery-promise/carriers/northline-freight.md) ·
[Stale stock handling](../reliability/stale-stock-handling.md)
