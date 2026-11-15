# Data Dictionary — Stock Record

Status: Draft · Owner: Nadia Kerr · Last updated: 2026-11-13

One stock record describes the sellable state of one SKU at one location. It is the input to every
availability number and therefore to every promise.

## Fields

| Field | Type | Required | Constraints | Example |
| :--- | :--- | :--- | :--- | :--- |
| `sku` | string(32) | Yes | Must exist in Atlas | `HH-GDP-4410` |
| `location_id` | string(24) | Yes | One of five known locations | `midlands-dc` |
| `on_hand` | integer | Yes | ≥ 0, ≤ 1,000,000 | `142` |
| `allocated` | integer | Yes | ≥ 0, ≤ `on_hand` | `18` |
| `quarantine` | integer | Yes | ≥ 0, ≤ `on_hand` | `4` |
| `condition` | enum | No | `new` (default), `open_box` | `new` |
| `open_reservations` | integer | Computed | ≥ 0 | `11` |
| `available` | integer | Computed | `on_hand - allocated - quarantine - open_reservations` | `109` |
| `feed_timestamp` | timestamp | Yes | Source clock, UTC | `2026-11-13T09:41:00Z` |
| `batch_id` | string(36) | Yes | Groups the batch | `mb-20261113-0941` |
| `sequence` | integer | Yes | Monotonic per source | `8842103` |
| `degraded` | boolean | Computed | True when the source is stale | `false` |

## Rules

1. `available` is never negative in a response. If the arithmetic produces a negative number, the
   record is flagged `inconsistent` and `available` returns 0, with an alert.
2. `quarantine` is mandatory, and a missing value is treated as 0 **with a logged warning**. It is never
   silently omitted.
3. `allocated` counts units on a pick list, not reservations. A reservation is not visible to a
   warehouse until allocation.
4. `condition = open_box` stock is available but must be quoted separately.
5. `sequence` older than the stored value is discarded, not applied.

## Example

```json
{
  "sku": "HH-GDP-4410",
  "location_id": "midlands-dc",
  "on_hand": 142,
  "allocated": 18,
  "quarantine": 4,
  "open_reservations": 11,
  "available": 109,
  "condition": "new",
  "feed_timestamp": "2026-11-13T09:41:00Z",
  "batch_id": "mb-20261113-0941",
  "sequence": 8842103,
  "degraded": false
}
```

## Where it comes from

| Field | Source | Transformation |
| :--- | :--- | :--- |
| `sku` | Warehouse feed | Mapped from warehouse code when they differ |
| `location_id` | Feed source | Canonical key, never the vendor's name |
| `on_hand` | Feed `ON_HAND` or `qty` | None |
| `allocated` | Feed `ALLOCATED` / `reserved_outbound` | Median of last three batches inside a wave window |
| `quarantine` | Feed field | Glasgow's personalisation hold split out |
| `open_reservations` | Reservation table | Count of `soft` and `allocated` |
| `degraded` | Staleness check | Per source threshold |

## Related

[Feed message](./feed-message.md) · [Reconciliation](../../stock-feeds/reliability/reconciliation.md) ·
[Data model](../../architecture/data-model.md)
