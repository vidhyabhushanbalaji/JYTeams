# Data Dictionary — Feed Message

Status: Draft · Owner: Dan Whitcombe · Last updated: 2026-11-13

The envelope and record shape every warehouse feed must produce. Four vendors implement it differently
internally; the ingestor sees only this.

## Batch envelope

| Field | Type | Required | Constraints | Example |
| :--- | :--- | :--- | :--- | :--- |
| `source` | string | Yes | `midlands-dc`, `glasgow-dc`, `northgate`, `riverside`, `stores` | `northgate` |
| `batch_id` | string(36) | Yes | Unique per source | `ng-20261113-0941` |
| `batch_timestamp` | timestamp | Yes | Source clock, UTC | `2026-11-13T09:41:00Z` |
| `cursor_from` | string | Delta only | Must match stored cursor | `8842100` |
| `cursor_to` | string | Delta only | New cursor | `8842118` |
| `record_count` | integer | Yes | Must match parsed rows | `2410` |
| `shape` | enum | Yes | `delta`, `snapshot` | `delta` |
| `schema_version` | integer | Yes | `1` | `1` |
| `records` | array | Yes | 1–250,000 | — |

## Record

| Field | Type | Required | Constraints | Example |
| :--- | :--- | :--- | :--- | :--- |
| `sku` | string(32) | Yes | Atlas code | `HH-GDP-4410` |
| `location_id` | string(24) | Yes | Canonical | `northgate` |
| `on_hand` | integer | Yes | ≥ 0 | `142` |
| `allocated` | integer | Yes | ≥ 0 | `18` |
| `quarantine` | integer | Yes | ≥ 0 | `4` |
| `condition` | enum | No | `new`, `open_box` | `new` |
| `updated_at` | timestamp | Yes | Per record | `2026-11-13T09:38:12Z` |
| `sequence` | integer | Yes | Monotonic | `8842117` |

## Validation outcomes

| Check | On failure | Effect |
| :--- | :--- | :--- |
| Envelope fields present and typed | Reject batch | Source goes stale |
| `record_count` matches rows | Reject batch | Source goes stale |
| Cursor matches stored | Request snapshot | Recovery is automatic |
| Row count within 5 % of previous | Reject batch | Guards truncation |
| `location_id` known | Reject batch | Configuration error |
| `sku` known | Quarantine row | One SKU missing, warning |
| Quantities sane | Quarantine row | One SKU missing, warning |

## Example batch

```json
{
  "source": "northgate",
  "batch_id": "ng-20261113-0941",
  "batch_timestamp": "2026-11-13T09:41:00Z",
  "cursor_from": "8842100",
  "cursor_to": "8842118",
  "record_count": 1,
  "shape": "delta",
  "schema_version": 1,
  "records": [
    { "sku": "HH-GDP-4410", "location_id": "northgate", "on_hand": 142,
      "allocated": 18, "quarantine": 4, "condition": "new",
      "updated_at": "2026-11-13T09:38:12Z", "sequence": 8842117 }
  ]
}
```

## Vendor mapping notes

| Vendor field | Maps to | Note |
| :--- | :--- | :--- |
| `ON_HAND`, `available`, `qty` | `on_hand` | Glasgow's `available` excludes holds; add them back first |
| `ALLOCATED`, `reserved_outbound` | `allocated` | — |
| `UNAVAILABLE`, `on_hold_client`, `quarantine` | `quarantine` | Never additive across fields |
| `PERSONALISATION_HOLD` | `quarantine` | Glasgow only, from release 8.4.2 |
| `inbound_pending` | Not mapped | Deliberately excluded from availability |

## Related

[Feed contracts](../../stock-feeds/protocol/feed-contracts.md) ·
[Delta and snapshot](../../stock-feeds/protocol/delta-and-snapshot.md) ·
[Stock feed API](../api/stock-feed-api.md)
