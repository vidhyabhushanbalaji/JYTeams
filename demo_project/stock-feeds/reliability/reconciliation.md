# Reconciliation

Status: Agreed · Owner: Ben Osei · Last updated: 2026-11-13

There are now three stock numbers rather than six: the availability service's figure, Mercury's
quantity, and Horizon's ledger. They will never be identical, and the point of this process is to
know exactly why they differ rather than to force them together.

## The three numbers

| Number | Meaning | Updated |
| :--- | :--- | :--- |
| Availability | Sellable now: `on_hand - allocated - quarantine - reserved` | Every feed cycle |
| Mercury quantity | Orders and routing view of stock | Every feed cycle, plus orders |
| Horizon ledger | Accounted stock value and quantity | Nightly at 01:00 |

## Expected differences

| Difference | Size | Explanation |
| :--- | :--- | :--- |
| Availability vs Mercury | 1–3 % | Reservations exist in availability, not in Mercury |
| Mercury vs Horizon | 0.4–1.8 % | Day's movements not yet posted to the ledger |
| Availability vs Horizon | 1–5 % | Both of the above, plus reservations |

The first line is new and is the one finance had to be persuaded about: reservations are a claim on
stock, not a movement of stock, so they belong in availability and not in the ledger.

## The daily job

Runs at 06:00, after the Horizon post, and produces one report per warehouse:

| Column | Example |
| :--- | :--- |
| SKU | `HH-GDP-4410` |
| Availability | 14 |
| Mercury | 16 |
| Horizon | 15 |
| Reservations open | 2 |
| Expected difference | −2 |
| Actual difference | −2 |
| Explained | Yes |

A row is "explained" when the availability figure equals Mercury minus open reservations, within a
tolerance of one unit per 1,000. Rows that are not explained are grouped by SKU and by warehouse and
reported.

## Tolerances

| Warehouse | Unexplained tolerance | Action above tolerance |
| :--- | :--- | :--- |
| Midlands DC | 0.5 % of SKUs in the report | Feed review with Dermot Shaw |
| Glasgow DC | 0.5 % | Feed review |
| Northgate | 0.3 % | Vendor call |
| Riverside | 1.0 % | Vendor call, given the data model quality |
| Stores | 6.0 % | Store support, weekly |

The store tolerance is high because store stock is 91 % accurate; holding stores to a warehouse
tolerance would produce a permanent exception list nobody reads.

## Monthly close

On working day 4, Horizon locks. The reconciliation report for the last day of the month is signed
off by Ben Osei and Sofia Mendes, and any unexplained difference above £10,000 in value is listed in
the close pack. Reservations are not part of the close, by design, and that decision is recorded in
[ADR 0008](../../decisions/0008-retain-mercury-as-order-system.md).

## What we would do with a big gap

| Size | Response |
| :--- | :--- |
| Under 1 % | Report, no action |
| 1–5 % | Investigate within 2 days; a feed may be drifting |
| 5–20 % | Hold the affected warehouse from availability; incident |
| Over 20 % | Hold the warehouse, notify the sponsor, review whether to roll back |

A 20 % gap is almost certainly a truncated snapshot rather than a real stock event, which is why the
snapshot completeness check exists upstream of this process.

## Related

[Delta and snapshot](../protocol/delta-and-snapshot.md) · [Horizon ERP](../../current-state/systems/horizon-erp.md) ·
[Stock record data dictionary](../../reference/data-dictionary/stock-record.md)
