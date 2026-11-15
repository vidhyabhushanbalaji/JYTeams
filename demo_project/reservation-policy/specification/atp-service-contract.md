# ATP Service Contract

Status: Draft · Owner: Nadia Kerr · Last updated: 2026-11-13

The availability service (ATP) answers one question: **how many of this SKU can be sold, from here,
with a date we can keep?** This contract is what callers can rely on; the endpoint reference is in
[availability API](../../reference/api/availability-api.md).

## Operations

| Operation | Purpose | Latency target | Callers |
| :--- | :--- | :--- | :--- |
| `quote` | Availability and promise for a set of lines | p95 180 ms | Storefront, marketplaces, contact centre |
| `read` | Current availability for one SKU | p95 40 ms | Internal, product pages |
| `reserve` | Create a soft reservation | p95 120 ms | Reservation worker only |
| `release` | Release a reservation with a reason | p95 120 ms | Reservation worker only |
| `health` | Per-warehouse feed freshness | p95 20 ms | Operations dashboard |

`quote` is the only operation a channel may call. Everything else is internal: the storefront cannot
create a reservation directly, because a reservation without an order is a stock leak.

## Quote semantics

A quote is **not** a reservation. It can be stale by up to the cache TTL (60 seconds) and it makes
no claim on stock. Two customers can both receive a quote for the last unit; only the reservation
decides who gets it.

| Field | Meaning |
| :--- | :--- |
| `sku` | Product identifier, never a marketplace identifier |
| `quantity_available` | Sellable units now, across eligible warehouses |
| `by_location[]` | Per-warehouse availability, with `stale` flag |
| `condition` | `new` or `open_box` pool |
| `delivery` | The promise, from DPS, or a fallback |
| `degraded` | True when any contributing feed is stale |

## Reservation semantics

| Rule | Contract |
| :--- | :--- |
| Idempotency | `(order_id, line_id, attempt)` is unique; a repeat returns the existing reservation |
| Atomicity | A multi-line reservation either reserves every line or none, unless the caller asks for partial |
| Expiry | Returned as an absolute timestamp, not a duration |
| Release | Requires a reason code from the agreed list |
| Ownership | Only the reservation worker may call `reserve` and `release` |

## Errors

| Code | HTTP | Meaning | Caller action |
| :--- | :--- | :--- | :--- |
| `ATP_STOCK_STALE` | 409 | No feed fresh enough to decide | Show fallback date, do not reserve |
| `ATP_INSUFFICIENT_STOCK` | 409 | Fewer units than requested | Offer partial options |
| `ATP_RESERVATION_EXPIRED` | 410 | Reservation no longer valid | Re-quote and re-reserve |
| `ATP_UNKNOWN_SKU` | 404 | Not in Atlas | Treat as unavailable |
| `ATP_LOCATION_UNAVAILABLE` | 409 | Warehouse on hold | Retry other locations |
| `ATP_RATE_LIMITED` | 429 | Caller over quota | Back off with `Retry-After` |

The distinction between 409 and 410 matters to the storefront: 409 means "ask again differently",
410 means "this order needs the customer's attention".

## Caching

| Layer | TTL | Why |
| :--- | :--- | :--- |
| Gateway response cache | 15 s | Absorbs product-page bursts |
| Service read cache | 60 s | Matches the Redis snapshot TTL |
| Client (storefront) | 10 s | Avoids re-requesting within one page render |
| Bypass | Reservation path | Never cached, always authoritative |

Caching is why `degraded` exists: a cached answer may be up to a minute old, and the flag tells the
caller whether the underlying feed was already stale when it was computed.

## Versioning and change

The contract is versioned `v1`. Adding a field is not a breaking change; changing a field's meaning
or removing one requires a new version and a migration window. `scorer_version` style metadata is
included in responses so a consumer can tell when behaviour changed.

## Related

[Availability API reference](../../reference/api/availability-api.md) · [ATP service](../../architecture/services/atp-service.md) ·
[Error codes](../../reference/api/error-codes.md)
