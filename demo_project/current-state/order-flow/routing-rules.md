# Routing Rules

Status: Agreed · Owner: Sofia Mendes · Last updated: 2026-11-03

Mercury decides which warehouse fulfils an order line using a rules table that has not changed
materially since 2023. It selects on channel, product attributes and a static warehouse priority,
and it has no knowledge of live stock levels.

## The rules, in priority order

| Priority | Rule | Applies to | Effect |
| :--- | :--- | :--- | :--- |
| 1 | Personalised or made-to-order | 2,100 SKUs | Always Glasgow DC, never split |
| 2 | Oversize or two-person delivery | 1,200 SKUs | Always Riverside Logistics |
| 3 | Channel contract | Amazon | Midlands DC first, Northgate second |
| 4 | Channel contract | eBay | Midlands, Northgate, Glasgow, Riverside |
| 5 | Store collection | Any | The chosen store only |
| 6 | Distance to postcode | All others | Nearest warehouse with a stock record |
| 7 | Warehouse priority | All others | Midlands 1, Glasgow 2, Northgate 3 |
| 8 | Fallback | No stock record | Hold for review, do not route |

## What "nearest" actually means

A static table of 12 postcode-area prefixes mapped to a preferred warehouse. It was built from
2019 delivery data and has never been recalculated. It routes 61 % of orders to Midlands DC even
though Glasgow is closer for 14 % of them, because the table only knows the first two characters of
the postcode.

## Splitting

If no single warehouse can satisfy every line, Mercury splits the order by warehouse and creates
separate dispatch records. The split is made **before** stock is checked, so 12 % of splits are
later consolidated or cancelled because one side had no stock. Customers are told about the split
only when the second parcel is dispatched.

## Overrides

| Override | Who | How often |
| :--- | :--- | :--- |
| Force a warehouse | Fulfilment team | 40–60 orders/day |
| Hold an order | Customer operations | 25/day, mostly address checks |
| Re-route after a stock failure | Fulfilment team | 90/day |

Overrides are free text in Mercury, which is why nobody can report on why they were used. The
reservation worker will not support free-text overrides; the replacement is a typed `hold` with a
reason code, and that is a change for the fulfilment team to accept during UAT.

## Why the rules have not changed

Two attempts to make routing stock-aware failed, in 2023 and 2025, because Mercury could only read
a stock snapshot that was already stale by the time routing ran overnight. The lesson recorded in
the discovery interviews is that routing needs **live** availability, not a better copy of a stale
one, which is why the platform computes availability centrally instead.

## What changes under Truestock

Routing itself stays in Mercury for this release (see
[ADR 0008](../../decisions/0008-retain-mercury-as-order-system.md)). What changes is that routing
is offered the ATP figure per warehouse and line, and it can choose a warehouse with unreserved
stock. The static postcode table is replaced by the carrier serviceability lookup for delivery
options, which is a smaller change with a measurable effect on split shipments.

## Related

[Batch windows](./batch-windows.md) · [Known failures](./known-failures.md) ·
[Mercury OMS](../systems/mercury-oms.md)
