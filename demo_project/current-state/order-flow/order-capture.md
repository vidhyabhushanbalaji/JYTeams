# Order Capture

Status: Agreed · Owner: Dan Whitcombe · Last updated: 2026-11-03

Every channel ends up in Mercury, but each gets there a different way and with different latency.
This document records the transport, the identifier and the failure behaviour for each, because
the reservation worker has to know when an order can be trusted to exist.

## Channel to Mercury

| Channel | Transport | First hop | Latency to Mercury | Retry behaviour |
| :--- | :--- | :--- | :--- | :--- |
| Website | Shopify webhook to Orbit | HTTPS | 8 s median, 40 s p95 | 3 retries, then dead-letter |
| Amazon | ChannelBridge pull | HTTPS poll | 5 min cadence | Retry next cycle |
| eBay | ChannelBridge pull | HTTPS poll | 5 min cadence | Retry next cycle |
| Wholesale portal | Direct service call | In-process | 2 s | Synchronous, user sees error |
| Wholesale EDI | File drop to Orbit | SFTP | 15 min cadence | Operator re-sends |
| Stores (collection) | Direct service call | In-process | 2 s | Synchronous |

## The order record

| Field | Source | Note |
| :--- | :--- | :--- |
| `order_id` | Mercury sequence | Not the channel's identifier |
| `channel_order_id` | Channel | Unique per channel, used for idempotency |
| `source` | Channel | `web`, `amazon`, `ebay`, `wholesale`, `store` |
| `placed_at` | Channel | Authoritative for promise calculation |
| `status` | Mercury | `pending`, `routed`, `allocated`, `dispatched`, `cancelled` |
| `lines[]` | Channel | SKU, quantity, unit price, personalisation flag |
| `delivery_postcode` | Channel | Used for serviceability, retained 90 days |

## Idempotency

The one rule that matters: `(source, channel_order_id)` is unique. A duplicate webhook is absorbed
by Mercury and logged, not rejected, because a rejected webhook triggers Shopify to retry for 48
hours. In October 2026 Mercury absorbed **1,840 duplicate webhooks**, which is 0.6 % of website
orders and entirely normal.

## Where capture fails

| Failure | Frequency | Consequence |
| :--- | :--- | :--- |
| Webhook lost, order only in Shopify | 3–6 per day | Customer service creates the order manually |
| Amazon `pending` order treated as confirmed | 11 in October | Stock reserved for an order that never completes |
| EDI file malformed | 2 per week | Wholesale desk keys the order in |
| Store collection call times out during POS update | 4 per month | Customer sees an error, order not created |

The Amazon pending case was fixed once in 2024 and regressed in a ChannelBridge upgrade in
September 2026; it is tracked as ISSUE-021's sibling and is on the integration test list.

## What changes under Truestock

Mercury remains the order system, so capture is unchanged apart from one addition: every accepted
order writes an `order.placed` event to the bus, including the channel and the `placed_at` time.
The reservation worker consumes that event rather than polling Mercury, which removes up to 90
seconds of delay at peak.

## Related

[Routing rules](./routing-rules.md) · [Mercury OMS](../systems/mercury-oms.md) ·
[Reservation events](../../reservation-policy/specification/reservation-events.md)
