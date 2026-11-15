# Mercury OMS

Status: Agreed · Owner: Ben Osei · Last updated: 2026-11-03

Mercury is our order management system: it holds every order, routes it to a warehouse, records the
dispatch and feeds the finance ledger. It is 11 years old, runs on a single SQL Server instance in
the Kettering data centre, and has an API that is a thin wrapper around stored procedures.

## What it does

| Function | Detail |
| :--- | :--- |
| Order storage | 41 m orders retained, 7 years |
| Routing | Rules table, see [routing rules](../order-flow/routing-rules.md) |
| Stock holding | A per-location quantity, updated by feeds and adjustments |
| Dispatch records | One per parcel, with carrier and tracking |
| Returns | Recorded against the original dispatch |
| Ledger feed | Nightly extract to Horizon at 01:00 |

## Interfaces

| Direction | Interface | Protocol | Owner |
| :--- | :--- | :--- | :--- |
| Inbound | Order creation | REST/JSON via Orbit | Dan Whitcombe |
| Inbound | Stock updates | Orbit batch, every 15 min | Dan Whitcombe |
| Inbound | Store stock file | Orbit batch, nightly | Elena Vasquez |
| Outbound | Route instructions | File to warehouse systems | Each warehouse |
| Outbound | Dispatch events | Kafka topic `mercury.dispatch` | Nadia Kerr |
| Outbound | Stock snapshot | SQL extract, every 30 min | Dan Whitcombe |

## Constraints that shaped the design

1. **No real-time stock API.** The only per-SKU read is a stored procedure that takes 300–900 ms
   per call and cannot be batched. A product page cannot call it.
2. **Routing is a scheduled run.** Orders placed after 22:00 are routed at 00:40.
3. **Stock is a number, not a ledger.** There is no history of why a quantity changed, only the
   current value plus the 30-day change log.
4. **Single instance.** No read replica; maintenance means downtime, negotiated weeks in advance.

## What Truestock does with it

Mercury stays as the order and routing system for this release
([ADR 0008](../../decisions/0008-retain-mercury-as-order-system.md)). It gains one outbound event
(`order.placed`) and one inbound capability: it may query ATP for a warehouse-level availability
figure when routing. It stops being the system of record for stock availability, which moves to the
availability service, but it still holds the quantity that finance reconciles against until the
post-peak review.

## Known risks

| Risk | Detail |
| :--- | :--- |
| Change log retention | 30 days only, so a stock dispute older than a month cannot be investigated |
| Stored procedures | No automated tests; a change is verified by running a week of orders in staging |
| Version drift | Production is on 8.4.2; UAT is on 8.4.2 with one hotfix that production lacks |
| Vendor support | The original vendor no longer exists; support is two contractors |

The last point is the reason for the "keep Mercury" decision: replacing it is a bigger programme
than Truestock, and doing both at once was rejected in September.

## Related

[Horizon ERP](./horizon-erp.md) · [Integration landscape](./integration-landscape.md) ·
[Order capture](../order-flow/order-capture.md)
