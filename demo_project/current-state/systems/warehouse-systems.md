# Warehouse Systems

Status: Agreed · Owner: Sofia Mendes · Last updated: 2026-11-03

Five locations hold stock, and no two use the same system. This document summarises what each
warehouse system can produce, how often, and what it cannot tell us, which is the starting point
for every feed contract in [stock-feeds](../../stock-feeds/).

## At a glance

| Location | Type | System | Vendor | Stock records | Feed today |
| :--- | :--- | :--- | :--- | :--- | :--- |
| Midlands DC (Kettering) | Own | DC-WMS | In-house, 2016 | 210,000 | Full snapshot, 15 min |
| Glasgow DC | Own | DC-WMS | In-house, 2016 | 96,000 | Full snapshot, 15 min |
| Northgate Fulfilment (Daventry) | 3PL | StockFlow | StockFlow Ltd | 148,000 | Delta, 15 min |
| Riverside Logistics (Bristol) | 3PL | LogiCore | LogiCore | 61,000 | Delta, 15 min |
| 184 stores | Own | StoreStock | In-house, 2019 | 41,000 lines | Full file, nightly |

## What each system exposes

### DC-WMS (Midlands and Glasgow)

A SQL view, `VW_AVAILABLE_STOCK`, refreshed on a 5-minute timer. It reports on-hand, allocated to
waves, and unavailable (quarantine, damage, quality hold). It has no concept of a future
reservation, because routing has always been the only thing that consumed stock.

### StockFlow (Northgate)

A REST endpoint returning a full inventory page set, 5,000 records per call, 30 pages for the full
estate. It also supports a delta endpoint, which is what we use. StockFlow distinguishes "available",
"reserved for outbound" and "on hold for client" — the last of these is Northgate's own client
quarantine and must never be sold.

### LogiCore (Riverside)

Bulk-oriented and slow: a delta endpoint that pages at 2,000 records and a full snapshot that takes
about 11 minutes to generate. It has the cleanest data model of the five, including explicit
"allocated" and "in transit" states.

### StoreStock

A nightly CSV of 41,000 lines sent by SFTP. One row per store per SKU with a quantity and a
last-counted timestamp. Many rows have a last-counted timestamp older than 90 days, which is the
mechanical explanation for the accuracy problem.

## What none of them can do

| Limitation | Consequence |
| :--- | :--- |
| No reservation acknowledgement | A warehouse cannot confirm it has accepted a hold |
| No pick-progress events | We learn about a pick only at dispatch |
| No cancellation callback | If we release stock, the warehouse finds out at the next poll |
| No per-order availability | Availability is per SKU per location, never per order |

The third row is the reason the platform needs a reason code on every release: without it, a
warehouse sees stock appear and cannot tell whether an order was cancelled or the reservation
expired.

## Related

[Stock feeds](../../stock-feeds/README.md) · [Midlands DC](../../stock-feeds/warehouses/midlands-dc.md) ·
[Store stock network](../../stock-feeds/warehouses/store-stock-network.md)
