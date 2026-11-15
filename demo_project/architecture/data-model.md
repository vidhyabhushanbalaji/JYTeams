# Data Model

Status: Draft · Owner: Nadia Kerr · Last updated: 2026-11-13

The tables the platform owns, what each row means, and how long it lives. Anything not listed here is
in Mercury, Horizon or Atlas and is not ours to change.

## Tables

| Table | Row means | Written by | Retention |
| :--- | :--- | :--- | :--- |
| `stock_snapshot` | Availability for one SKU at one location | Ingestor | 7 days (last 3 per source kept) |
| `feed_batch` | One received batch | Ingestor | 30 days |
| `feed_quarantine` | One rejected row | Ingestor | 30 days |
| `reservation` | One claim on stock | Reservation worker | 90 days |
| `reservation_event` | One state change | Reservation worker | 90 days |
| `promise` | One date promised to one shipment | DPS | 30 days rolling |
| `policy_config` | One configuration key | Admin console | Audit log permanent |
| `location` | One warehouse or store | Migration | Static |

## `stock_snapshot`

| Column | Type | Notes |
| :--- | :--- | :--- |
| `sku` | text | Atlas code |
| `location_id` | text | Canonical location |
| `on_hand` | integer | Physical |
| `allocated` | integer | Committed to picks |
| `quarantine` | integer | Never sellable |
| `condition` | enum | `new`, `open_box` |
| `feed_timestamp` | timestamptz | Source clock |
| `batch_id` | text | Groups the batch |
| `sequence` | bigint | Monotonic per source |

A row is replaced, not versioned, except that the last three batches per source are kept for the
median-allocated mitigation described in
[Midlands DC](../stock-feeds/warehouses/midlands-dc.md).

## `reservation`

| Column | Type | Notes |
| :--- | :--- | :--- |
| `id` | uuid | Sortable, ULID-style |
| `order_id` | text | Mercury order |
| `line_id` | integer | Order line |
| `shipment_id` | integer | Split shipment |
| `sku`, `location_id` | text | The unit |
| `quantity` | integer | Usually 1 |
| `state` | enum | `soft`, `allocated`, `dispatched`, `released`, `expired` |
| `expires_at` | timestamptz | Absolute |
| `reason_code` | text | Required on release |
| `created_at`, `updated_at` | timestamptz | — |

Unique constraint on `(order_id, line_id, attempt)` gives idempotency. An index on
`(sku, location_id, state)` is what makes the reservation check fast under contention.

## `promise`

| Column | Type | Notes |
| :--- | :--- | :--- |
| `id` | uuid | — |
| `order_id`, `shipment_id` | text, integer | — |
| `service` | text | `parcel_next_day` etc. |
| `promised_date` | date | The day we told the customer |
| `assumed_stock_age_seconds` | integer | Audit of the input |
| `fallback_used` | boolean | True when no date was possible |
| `fallback_reason` | text | Why |
| `created_at` | timestamptz | — |

`promised_date` is never updated. A change creates a new row with `supersedes_id`, so accuracy can be
measured against what was actually said.

## Relationships

```text
location 1──n stock_snapshot n──1 sku (Atlas, external)
order 1──n reservation 1──n reservation_event
order 1──n promise (one per shipment)
reservation n──1 promise? no: promises are per shipment, independent of reservations
```

Reservations and promises are deliberately not foreign-keyed to each other. A promise can exist for a
pre-order with no reservation, and a reservation can exist for a wholesale order with no promise.

## Indexes that matter

| Index | Why |
| :--- | :--- |
| `reservation (sku, location_id, state)` | Reservation check under contention |
| `reservation (expires_at) where state='soft'` | Expiry sweep |
| `stock_snapshot (location_id, sku)` | Availability read |
| `promise (promised_date, service)` | Accuracy reporting |
| `feed_quarantine (batch_id)` | Daily digest |

## Data protection

| Data | Classification | Handling |
| :--- | :--- | :--- |
| SKU, location | Internal | No restriction |
| Reservation | Internal | Contains order ID only |
| Promise | Internal plus postcode district | Postcode district only |
| Feed payloads | Internal | Deleted after 30 days |
| Customer name | Not stored | Lives in Mercury only |

The platform deliberately stores no customer name, address or email. It knows an order ID and a
postcode district, which is enough to promise and not enough to identify.

## Related

[Stock record dictionary](../reference/data-dictionary/stock-record.md) ·
[Reservation record](../reference/data-dictionary/reservation-record.md) ·
[Promise record](../reference/data-dictionary/promise-record.md)
