# Data Dictionary — Promise Record

Status: Draft · Owner: Gavin Shore · Last updated: 2026-11-13

One promise is one date given to one shipment. It is stored, never edited, because promise accuracy is
measured against what the customer was actually told.

## Fields

| Field | Type | Required | Constraints | Example |
| :--- | :--- | :--- | :--- | :--- |
| `id` | ulid | Yes | Unique | `01HQ7ZK4AA` |
| `order_id` | string(24) | Yes | Mercury order | `MH-4821993` |
| `shipment_id` | integer | Yes | 1–3 | `1` |
| `service` | enum | Yes | See service list | `parcel_next_day` |
| `location_id` | string(24) | Yes | Serving warehouse | `midlands-dc` |
| `postcode_district` | string(8) | Yes | e.g. `CV21`, never the full postcode | `CV21` |
| `promised_date` | date | When known | Business day | `2027-05-20` |
| `promised_week` | date | When no day possible | Monday of the week | `2027-06-07` |
| `assumed_stock_age_seconds` | integer | Yes | From the availability response | `372` |
| `fallback_used` | boolean | Yes | True when no date was possible | `false` |
| `fallback_reason` | enum | When fallback | See below | — |
| `supersedes_id` | ulid | No | Previous promise for this shipment | — |
| `created_at` | timestamp | Yes | UTC | `2027-05-19T09:00:06Z` |

## Exactly one of date or week

A record carries either `promised_date` or `promised_week`, never both and never neither, except in the
fallback case where both are null and `fallback_used` is true. A database check enforces the three
permitted shapes.

## Fallback reasons

| Reason | Meaning |
| :--- | :--- |
| `stock_stale` | No fresh feed for any contributing warehouse |
| `platform_degraded` | DPS or ATP unavailable |
| `carrier_unavailable` | Serviceability could not be established |
| `calendar_unavailable` | Calendar older than 24 hours |

## Services

| Value | Customer name | Lead time |
| :--- | :--- | :--- |
| `parcel_next_day` | Next Day | 1 working day |
| `parcel_saturday` | Saturday Delivery | Saturday |
| `parcel_two_day` | Standard | 2 working days |
| `locker_24h` | Collect from a locker | 1 working day |
| `bulky_two_person` | Room of Choice | 3–5 working days |
| `bulky_named_day` | Choose Your Day | 3–7 working days |
| `bulky_assembly` | Delivered and Assembled | 5–7 working days |
| `collection` | Collect from store | Ready next day |

## Why the stock age is stored

`assumed_stock_age_seconds` is the audit trail. When a promise turns out wrong, the first question is
what the platform believed about stock at the time, and this field, combined with the feed batch
records, answers it without guesswork.

## Related

[Promise accuracy](../../delivery-promise/customer-messaging/promise-accuracy.md) ·
[Delivery date logic](../../delivery-promise/calculation/delivery-date-logic.md) ·
[Data model](../../architecture/data-model.md)
