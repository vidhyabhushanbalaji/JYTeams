# Policy Configuration

Status: Draft · Owner: Sofia Mendes · Last updated: 2026-11-13

The rules are business decisions, so they are configuration rather than code. This document lists
every key, its default and who may change it. A key not listed here does not exist.

## Keys

| Key | Default | Range | Owner | Effect |
| :--- | :--- | :--- | :--- | :--- |
| `reservation.soft_ttl_seconds` | 1800 | 300–3600 | Sofia Mendes | Soft reservation life |
| `reservation.capture_ttl_seconds` | 3600 | 1800–7200 | Sofia Mendes | Life after capture confirmation (RSV-02) |
| `reservation.expiry_sweep_seconds` | 60 | 30–300 | Nadia Kerr | Expiry job interval |
| `reservation.max_shipments` | 3 | 1–5 | Sofia Mendes | Split shipment cap |
| `reservation.store_pick_seconds` | 1800 | 900–7200 | Elena Vasquez | Store pick window |
| `reservation.collection_hold_days` | 5 | 3–7 | Elena Vasquez | Collection hold (RSV-11, open) |
| `reservation.bulky_mode` | `at_order` | `at_order`, `at_booking` | Sofia Mendes | RSV-06, open |
| `availability.cache_ttl_seconds` | 60 | 10–300 | Nadia Kerr | Redis snapshot TTL |
| `availability.gateway_ttl_seconds` | 15 | 0–60 | Nadia Kerr | Response cache TTL |
| `availability.quote_max_lines` | 40 | 10–100 | Nadia Kerr | Basket size limit |
| `stale.midlands_minutes` | 15 | 5–60 | Dan Whitcombe | Stale threshold |
| `stale.glasgow_minutes` | 15 | 5–60 | Dan Whitcombe | Stale threshold |
| `stale.northgate_minutes` | 20 | 5–60 | Dan Whitcombe | Stale threshold |
| `stale.riverside_minutes` | 45 | 15–120 | Dan Whitcombe | Stale threshold |
| `stale.store_minutes` | 90 | 60–1440 | Elena Vasquez | Collection only |
| `backorder.max_days` | 28 | 7–60 | Tom Alder | Consumer backorder cap |
| `preorder.reserve_days_before` | 7 | 3–14 | Tom Alder | Pre-order release window |
| `promise.bank_holiday_buffer_hours` | 6 | 0–24 | Gavin Shore | RSV-19 |
| `promise.fallback_days` | 5 | 3–10 | Tom Alder | Fallback when DPS is down |
| `hold.warehouse` | empty | warehouse ids | Marcus Feld | Manual hold switch (RSV-18) |

## Who can change what

| Role | May change | Process |
| :--- | :--- | :--- |
| Policy owner | Any `reservation.*` or `promise.*` key | Written note in the rule table, then the change |
| Platform lead | Any `availability.*` or `stale.*` key | Change request, deploy, verify |
| Fulfilment manager | `hold.warehouse` | Immediate, must be logged |
| Anyone else | Nothing | Ask the owner |

Business keys are changed through a small admin screen and take effect on the next reservation,
without a deploy. Technical keys are changed by deployment, because a 60-second cache TTL and a
5-minute one behave differently under load and that needs a test.

## Example

```yaml
reservation:
  soft_ttl_seconds: 1800
  capture_ttl_seconds: 3600
  bulky_mode: at_order
  collection_hold_days: 5
stale:
  midlands_minutes: 15
  riverside_minutes: 45
promise:
  fallback_days: 5
```

## Change log

| Date | Key | From | To | Why |
| :--- | :--- | :--- | :--- | :--- |
| 2026-10-22 | `reservation.soft_ttl_seconds` | 900 | 1800 | 15 minutes expired before capture on 3 % of orders |
| 2026-11-05 | `stale.riverside_minutes` | 25 | 45 | Snapshot generation takes 11 min; daily false stales |
| 2026-11-12 | `availability.cache_ttl_seconds` | 120 | 60 | Trading asked for fresher product-page figures |
| 2026-11-13 | `reservation.bulky_mode` | `at_booking` | `at_order` | Provisional, awaiting the 2026-12-03 decision |

## Related

[Reservation rules](../policy/reservation-rules.md) · [Oversell prevention](../policy/oversell-prevention.md) ·
[Stock record data dictionary](../../reference/data-dictionary/stock-record.md)
