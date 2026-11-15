# Event Flows

Status: Draft · Owner: Nadia Kerr · Last updated: 2026-11-13

Five flows, end to end, with the timing a customer experiences. If a document in this repository
disagrees with these, the flows are wrong or the document is; either way it is a defect.

## 1. A website order

```text
Shopify ──webhook──▶ Orbit ──▶ Integration hub ──order.placed──▶ Kafka
                                                                    │
                                                    ┌───────────────▼───────────────┐
                                                    │ Reservation worker            │
                                                    │ quote → reserve → promise     │
                                                    └───────────────┬───────────────┘
                                                                    │
                                        reservation.created + promise.issued
                                                                    │
                                                                    ▼
                                                    Confirmation email, agent screen
```

| Step | Budget | Failure |
| :--- | :--- | :--- |
| Webhook to hub | 8 s p95 | Retry, dead letter |
| Order event to reservation | 2 s p95 | Retry, then fallback to polling |
| Reservation to promise | 300 ms | Promiseless order, flagged |
| Confirmation | 60 s | Email delayed, order fine |

## 2. A stock change

```text
Warehouse ──poll──▶ Ingestor ──validate──▶ compute availability
                                                │
                                    stock.changed (changed SKUs only)
                                                │
                              ┌─────────────────┴────────────────┐
                              ▼                                  ▼
                       Redis cache update                Postgres snapshot
                              │
                              ▼
                    Next quote is fresh (≤60 s)
```

Only changed SKUs are published. A 210,000-row snapshot with 400 changes produces 400 events, not
210,000.

## 3. A promise calculation

```text
ATP ──quote──▶ DPS ──serviceability──▶ Carrier
                 │                        │
                 │◀────services, lead time
                 │
                 ├── calendar (cache 24 h)
                 ├── cut-off configuration
                 └── buffer rules
                          │
                          ▼
                    promise.issued (stored)
```

The promise is stored because accuracy is measured against what was said. Recomputing it later would
produce a flattering number.

## 4. A cancellation

```text
Customer ──▶ Shopify ──▶ Mercury ──order.cancelled──▶ Kafka
                                                         │
                                            ┌────────────▼────────────┐
                                            │ Reservation worker      │
                                            │ release(reason)         │
                                            └────────────┬────────────┘
                                                         │
                            reservation.released ────────┴──────▶ Ingestor→warehouse
                                                                  │
                                                                  ▼
                                                       Availability returns
```

## 5. Dispatch

```text
Mercury ──dispatch──▶ Integration hub ──▶ carrier booking ──▶ label
                            │
                            ├── reservation.dispatched
                            ├── marketplace tracking upload
                            └── customer dispatch email
```

## Timing, end to end

| From | To | Typical | Worst |
| :--- | :--- | :--- | :--- |
| Order placed | Reservation exists | 12 s | 90 s |
| Order placed | Customer sees confirmation | 45 s | 5 min |
| Warehouse change | Availability updated | 5 min 30 s | 20 min |
| Cancellation | Stock available again | 3 s | 15 min (warehouse poll) |
| Allocation | Dispatch | Wave-dependent | — |

## What can go wrong, and where it is handled

| Failure point | Consequence | Handling |
| :--- | :--- | :--- |
| Hub does not receive the webhook | Order exists, no reservation | Polling fallback, alert |
| Reservation fails | Order without a promise | Retry, then flag for support |
| Promise calculation fails | No date | Fallback estimate, logged reason |
| Event duplicate | Double reservation | Idempotency on `(order, line, attempt)` |
| Event out of order | Stale state applied | Sequence check per SKU |
| Warehouse never sees the release | Stock appears late there | Next poll, reason code explains |

## Related

[Reservation events](../reservation-policy/specification/reservation-events.md) ·
[Data model](./data-model.md) · [Integration hub](./services/integration-hub.md)
