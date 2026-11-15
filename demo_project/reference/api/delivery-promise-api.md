# Delivery Promise API

Status: Draft · Owner: Gavin Shore · Last updated: 2026-11-13

Endpoint reference for the delivery promise service (DPS). It computes dates, stores them, and answers
questions about them. It never books a delivery.

## Base

```text
https://api.harbourandheath.internal/promise/v1
```

## `POST /promise`

Called by ATP during a quote, and directly by the reservation worker when storing the promise.

```json
{
  "order_id": "MH-4821993",
  "shipment_id": 1,
  "postcode": "CV21 4DJ",
  "location_id": "midlands-dc",
  "service": "parcel_next_day",
  "assumed_stock_age_seconds": 372,
  "placed_at": "2027-05-19T09:00:00Z"
}
```

Response:

```json
{
  "promise_id": "01HQ7ZK4AA",
  "service": "parcel_next_day",
  "promised_date": "2027-05-20",
  "cut_off_used": "12:30",
  "buffer_applied": false,
  "fallback": false
}
```

| Field | Meaning |
| :--- | :--- |
| `promised_date` | A day, when a day can be defended |
| `promised_week` | Monday of the week, for bulky beyond the horizon |
| `cut_off_used` | Audit of which cut-off applied |
| `buffer_applied` | True in a bank holiday week |
| `fallback` | True when no date was possible |

## `POST /serviceability`

| Field | Required | Notes |
| :--- | :--- | :--- |
| `postcode` | Yes | Full postcode |
| `weight_grams` | Yes | Drives the service list |
| `length_cm`, `width_cm`, `height_cm` | Yes | Excludes lockers and parcels above limits |
| `quantity` | No | Multi-unit orders may exceed parcel limits |

Response per service:

```json
{ "service": "bulky_two_person", "available": true, "lead_days": 5,
  "slot_horizon_days": 14, "surcharge": 19.95, "restrictions": ["kerbside_only"] }
```

## `GET /promise/{order_id}`

Returns every stored promise for an order, newest first, including superseded records.

| Field | Meaning |
| :--- | :--- |
| `promises[]` | One per shipment, with `supersedes_id` |
| `changes[]` | Dates that changed, with the reason |

The contact centre screen uses this endpoint rather than Mercury, which is how agents and customers see
the same date.

## `POST /promise/{id}/recalculate`

Used after an address change or a re-route. It does **not** edit the original record: it creates a new
promise that supersedes it.

| Status | Meaning |
| :--- | :--- |
| 201 | New promise created |
| 409 | No serviceable service; fallback offered |
| 422 | Shipment already dispatched |

## Caching headers

| Response | `Cache-Control` |
| :--- | :--- |
| `/serviceability` | `max-age=300` at the gateway, 24 h at the service |
| `/promise` | `no-store` |
| `/promise/{order_id}` | `no-store` |

Quotes are cached because they are frequent and non-committal; promises are not cached because the
customer is entitled to the current answer.

## Rate limits

| Caller | Limit |
| :--- | :--- |
| ATP | 900 per minute |
| Reservation worker | 300 per minute |
| Storefront direct | Not permitted |

## Related

[Delivery date logic](../../delivery-promise/calculation/delivery-date-logic.md) ·
[Promise record](../data-dictionary/promise-record.md) · [Error codes](./error-codes.md)
