# Data Dictionary — Reservation Record

Status: Draft · Owner: Nadia Kerr · Last updated: 2026-11-13

One reservation is one claim on stock by one order line. The record is the audit trail of the promise
made to a customer, and it is the only place a claim can be created or ended.

## Fields

| Field | Type | Required | Constraints | Example |
| :--- | :--- | :--- | :--- | :--- |
| `id` | ulid | Yes | Unique, sortable | `01HQ7ZK3M9` |
| `order_id` | string(24) | Yes | Exists in Mercury | `MH-4821993` |
| `line_id` | integer | Yes | ≥ 1 | `2` |
| `shipment_id` | integer | Yes | ≥ 1, ≤ 3 | `1` |
| `attempt` | integer | Yes | ≥ 1 | `1` |
| `sku` | string(32) | Yes | Atlas | `HH-GDP-4410` |
| `location_id` | string(24) | Yes | Canonical | `midlands-dc` |
| `quantity` | integer | Yes | ≥ 1, usually 1 | `1` |
| `state` | enum | Yes | See below | `soft` |
| `reason_code` | enum | On release | One of eight | `PAYMENT_FAILED` |
| `expires_at` | timestamp | For soft | `created_at + TTL` | `2026-11-13T10:11:00Z` |
| `created_at` | timestamp | Yes | UTC | `2026-11-13T09:41:00Z` |
| `updated_at` | timestamp | Yes | UTC | — |
| `channel` | enum | Yes | `web`, `amazon`, `ebay`, `wholesale`, `store` | `web` |

## States

| State | Counts against availability | Terminal |
| :--- | :--- | :--- |
| `soft` | Yes | No |
| `allocated` | Yes | No |
| `dispatched` | Yes, until the next feed removes it | Yes |
| `released` | No | Yes |
| `expired` | No | Yes |

## Uniqueness

`(order_id, line_id, attempt)` is unique. A duplicate event returns the existing record rather than
creating a second claim. This constraint, not application logic, is what makes a replayed order event
safe.

## Example

```json
{
  "id": "01HQ7ZK3M9",
  "order_id": "MH-4821993",
  "line_id": 2,
  "shipment_id": 1,
  "attempt": 1,
  "sku": "HH-GDP-4410",
  "location_id": "midlands-dc",
  "quantity": 1,
  "state": "soft",
  "expires_at": "2026-11-13T10:11:00Z",
  "created_at": "2026-11-13T09:41:00Z",
  "channel": "web"
}
```

## Reason codes

| Code | Set by | Visible to warehouse |
| :--- | :--- | :--- |
| `CUSTOMER_CANCELLED` | Worker | Yes |
| `PAYMENT_FAILED` | Worker | Yes |
| `RESERVATION_EXPIRED` | Expiry job | Yes |
| `NOT_COLLECTED` | Worker | Yes |
| `WAREHOUSE_REJECTED` | Warehouse | Yes |
| `SKU_DISCONTINUED` | Worker | No |
| `STOCK_CORRECTION` | Worker | No |
| `MANUAL_OVERRIDE` | Console | Yes |

## What is deliberately absent

No customer name, address, email or price. The record identifies an order and a unit; everything else
lives in Mercury, which is where the customer already is.

## Related

[Reservation lifecycle](../../reservation-policy/policy/reservation-lifecycle.md) ·
[Reservation events](../../reservation-policy/specification/reservation-events.md) ·
[Data model](../../architecture/data-model.md)
