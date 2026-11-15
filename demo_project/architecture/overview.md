# Overview

Status: Draft · Owner: Nadia Kerr · Last updated: 2026-11-13

The platform in one page: what runs, what talks to what, and where the data lives.

## Diagram

```text
                   ┌──────────────┐        ┌────────────────┐
Warehouses ───────▶│ Feed ingestor│───────▶│    Postgres    │
(cursor, poll)     └──────┬───────┘        │  stock, feed   │
                          │ stock.changed  └───────┬────────┘
                          ▼                        │
                   ┌──────────────┐                │
                   │     Kafka    │                ▼
                   │ truestock-   │        ┌──────────────┐      ┌───────┐
                   │    events    │───────▶│  ATP service │◀────▶│ Redis │
                   └──────┬───────┘        └──────┬───────┘      └───────┘
                          │                       │ quote/read
        order.placed      │                       ▼
                          ▼                 ┌───────────────┐
                   ┌──────────────┐         │  Storefront   │
                   │ Reservation  │         │  Marketplaces │
                   │   worker     │         │ Contact centre│
                   └──────┬───────┘         └───────────────┘
                          │ reserve/release
                          ▼
                   ┌──────────────┐   serviceability   ┌──────────┐
                   │ Promise (DPS)│───────────────────▶│ Carriers │
                   └──────────────┘◀───────────────────└──────────┘
```

## Request paths

| Path | Who calls | Latency budget |
| :--- | :--- | :--- |
| Quote | Storefront, marketplaces | 180 ms p95 |
| Read | Product pages, internal | 40 ms p95 |
| Reserve | Reservation worker only | 120 ms p95 |
| Promise | ATP, checkout | 90 ms p95 (cached 60 s) |
| Serviceability | DPS, checkout | 250 ms p95 (cached 24 h) |

## Component responsibilities

| Component | Does | Does not |
| :--- | :--- | :--- |
| Feed ingestor | Poll, validate, compute availability, publish | Decide policy |
| ATP service | Answer availability, create/release reservations via worker | Call carriers |
| Reservation worker | Own the reservation state machine | Compute dates |
| DPS | Compute and store promises | Know about stock counts |
| Integration hub | Order and dispatch events, Orbit bridging | Business rules |
| Storefront | Display and take payment | Reserve directly |

## Data ownership

| Data | Owner | Written by |
| :--- | :--- | :--- |
| Stock snapshot | Ingestor | Ingestor only |
| Reservation | Reservation worker | Worker only |
| Promise | DPS | DPS only |
| Configuration | Policy admin | Named owners, audited |
| Feed batch | Ingestor | Ingestor only |

"Written by" is an architectural rule, not a convention. A service that writes another service's data
has broken the boundary, and availability and reservations are exactly where that would be dangerous.

## What is not in the platform

| Not here | Lives in |
| :--- | :--- |
| Order storage and routing | Mercury |
| Stock ledger and accounting | Horizon |
| Product data | Atlas |
| Payment | Payment provider, via Shopify |
| Warehouse picking | DC-WMS, StockFlow, LogiCore, StorePOS |
| Integration mappings for EDI | Orbit |

## Scale

| Dimension | Baseline | Peak |
| :--- | :--- | :--- |
| Availability quotes | 151/s | 574/s |
| Reservations | 8/s | 31/s |
| Feed events/hour | 6,100 | 12,000 |
| Postgres rows (stock) | 556,000 | 556,000 |

## Related

[System context](./system-context.md) · [Event flows](./event-flows.md) ·
[Services](./services/)
