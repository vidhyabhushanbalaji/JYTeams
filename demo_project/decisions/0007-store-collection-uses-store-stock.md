# 0007 — Store Collection Uses Store Stock

Status: Accepted · Date: 2026-10-23 · Deciders: Elena Vasquez, Sofia Mendes, Tom Alder

## Context

Collection orders promise a store's own stock, but that stock is 91 % accurate and arrives nightly.
18 % of collection orders are cancelled because the item cannot be found, and the customer often learns
by email hours later.

Two questions were open: should collection draw on a central pool, and should stores reserve at pick
time or at order time.

## Options

| Option | Accuracy | Complexity | Customer experience |
| :--- | :--- | :--- | :--- |
| A. Store stock, reserve at order | 91 % data, fast failure | Medium | Told within 30 minutes |
| B. Store stock, reserve at pick | Same data, slower failure | Low | Told hours later |
| C. Central pool, transfer to store | High accuracy, 1–2 day delay | High | No "today" collection |
| D. Collection only from scanner-equipped stores | 96 % | Low | 96 of 184 stores |

## Decision

Collection uses **store stock**, with a **30-minute pick reservation at order time** and a five-day
collection hold, and stores without scanners stay in scope.

## Why not a central pool

Option C would be more accurate and would destroy the product: collection exists because the customer
wants it today, and a transfer makes it a slower delivery with an extra step. It was rejected by trading
and store operations together.

## Why not scanner-only

Option D is tempting and unfair: the 88 stores without scanners serve the customers with the fewest
alternatives. Excluding them would improve a metric by withdrawing a service.

## Consequences

| Easier | Harder |
| :--- | :--- |
| Stores learn about a problem in 30 minutes | 9 % of reservations are for stock that does not exist |
| The unit is protected from other channels | Reservation accuracy cannot exceed stock accuracy |
| Pick tasks replace printouts | Store task API is a dependency (FS-10 failing) |
| Collection promise becomes measurable per store | Uncollected holds tie up shelf space for 5 days |

## The honest limitation

This decision deliberately does not fix store accuracy. It moves the discovery of an error earlier,
which is a real improvement (22 % → 70 % of failures found within an hour) and not the same thing as
accuracy. The collection promise target of 88 % reflects that.

## Related

[Store collection](../reservation-policy/edge-cases/store-collection.md) ·
[Store stock network](../stock-feeds/warehouses/store-stock-network.md) ·
[Stores](../current-state/channels/stores.md)
