# Availability API

Status: Draft · Owner: Nadia Kerr · Last updated: 2026-11-13

The endpoint reference for the availability service. Behavioural rules are in the
[ATP service contract](../../reservation-policy/specification/atp-service-contract.md); this page is the
shape of the calls.

## Base

```text
https://api.harbourandheath.internal/availability/v1
```

Internal only. Channels reach it through the storefront or the marketplace adapter, never directly.

## `POST /quote`

```json
{
  "postcode": "CV21 4DJ",
  "channel": "web",
  "lines": [
    { "sku": "HH-GDP-4410", "quantity": 1 },
    { "sku": "HH-FUR-2210", "quantity": 2 }
  ]
}
```

| Field | Required | Notes |
| :--- | :--- | :--- |
| `postcode` | Yes | Full postcode for serviceability |
| `channel` | Yes | `web`, `amazon`, `ebay`, `wholesale`, `store` |
| `lines` | Yes | 1–40 lines |
| `store_id` | For collection | Required when `channel=store` |

Response:

```json
{
  "degraded": false,
  "lines": [
    { "line": 1, "sku": "HH-GDP-4410", "requested": 1, "available": 14,
      "shape": "full", "by_location": [ { "location_id": "midlands-dc", "available": 14, "stale": false } ],
      "delivery": { "service": "parcel_next_day", "date": "2027-05-20" } },
    { "line": 2, "sku": "HH-FUR-2210", "requested": 2, "available": 0,
      "shape": "none", "delivery": { "fallback": true, "reason": "stock_stale" } }
  ]
}
```

| Field | Meaning |
| :--- | :--- |
| `shape` | `full`, `partial`, `none` |
| `available` | Sellable units now, at the best location |
| `by_location[]` | Per-warehouse detail, with `stale` |
| `delivery` | A date, a week, or a fallback |
| `degraded` | Any contributing source stale |

## `GET /availability/{sku}`

Returns the single-SKU view used by product pages and internal tools.

| Query | Default | Notes |
| :--- | :--- | :--- |
| `postcode` | — | Optional; affects the date only |
| `condition` | `new` | `open_box` returns the separate pool |

## `POST /reservations`

Internal. Called only by the reservation worker.

```json
{ "order_id": "MH-4821993", "line_id": 2, "shipment_id": 1,
  "sku": "HH-GDP-4410", "quantity": 1, "location_id": "midlands-dc" }
```

| Status | Meaning |
| :--- | :--- |
| 201 | Created, with `expires_at` |
| 200 | Existing reservation returned (idempotent repeat) |
| 409 | Insufficient stock or stale |
| 410 | Reservation no longer valid |

## `POST /reservations/{id}/release`

```json
{ "reason_code": "CUSTOMER_CANCELLED", "released_by": "reservation-worker" }
```

A release without a valid reason code returns 422 and is **not** applied. That is deliberate: a silent
release is the failure mode this platform exists to remove.

## `GET /health`

| Field | Meaning |
| :--- | :--- |
| `sources[]` | Per-source `last_good`, `stale`, `threshold_seconds` |
| `cache` | Redis status and hit rate |
| `version` | Build and schema version |

## Rate limits

| Caller | Limit |
| :--- | :--- |
| Storefront | 1,200 per minute per instance |
| Marketplace adapter | 900 per minute |
| Internal services | No limit, but quota alerts at 10× normal |

## Related

[ATP service contract](../../reservation-policy/specification/atp-service-contract.md) ·
[Error codes](./error-codes.md) · [ATP service](../../architecture/services/atp-service.md)
