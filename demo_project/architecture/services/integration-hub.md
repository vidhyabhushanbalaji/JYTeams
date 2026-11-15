# Integration Hub

Status: Draft · Owner: Dan Whitcombe · Last updated: 2026-11-13

The bridge between what exists and what is new. It translates Mercury orders into events, dispatch
events into marketplace confirmations, and keeps Orbit's file traffic where it still belongs.

## Responsibilities

| Does | Does not |
| :--- | :--- |
| Publish `order.placed` and `order.cancelled` | Store orders |
| Publish `reservation.dispatched` | Own reservation state |
| Upload marketplace tracking | Manage marketplace listings |
| Bridge Orbit file traffic | Replace Mercury routing |
| Retry with idempotency | Decide business rules |

## Inbound

| Source | Message | Transformation |
| :--- | :--- | :--- |
| Shopify webhook | `orders/create` | Map to order event, idempotent on channel order ID |
| ChannelBridge | Amazon and eBay orders | Map to the same event shape |
| Mercury | `order.cancelled` | Pass through with reason |
| Mercury | `dispatch` | Pass through with parcels and tracking |
| Trade portal | Order created | Same event shape |

Every inbound message is normalised to one envelope, so the reservation worker has one contract
regardless of channel.

## Outbound

| Destination | Message | Failure |
| :--- | :--- | :--- |
| Kafka | Domain events | Retry, dead letter |
| ChannelBridge | Inventory push, tracking upload | Retry per cycle, alert after 3 |
| Orbit | EDI acknowledgements, dispatch files | Retry, operator visible |
| Carriers | Booking requests | Queue, then retry |

## Falling back to polling

If Kafka is unavailable, the hub can poll Mercury's order table every 30 seconds. This path exists
because FS-07 showed the platform would otherwise stop reserving entirely during an event-bus outage.

| Property | Value |
| :--- | :--- |
| Poll interval | 30 s |
| Watermark | Last processed order timestamp |
| Overlap | 5 minutes, absorbed by idempotency |
| Activation | Automatic after 60 s without events, alert raised |

## Ordering

| Message | Ordering key |
| :--- | :--- |
| `order.placed` | `order_id` |
| `order.cancelled` | `order_id` |
| `reservation.dispatched` | `order_id` |
| `stock.changed` | `sku` |

Order events for one order are ordered; events for different orders may interleave. The partition key
is deliberately the order, not the SKU, because a cancellation must not overtake its own placement.

## What Orbit keeps

| Traffic | Stays in Orbit |
| :--- | :--- |
| EDI 850/855/856 | Yes |
| Store stock file transfer | Yes |
| Dispatch files to DC-WMS | Yes |
| Marketplace inventory | No: moves to the hub |
| Warehouse stock polls | No: moves to the ingestor |

After the release, Orbit carries about 40 % of its current message volume. Retiring it entirely is a
post-peak conversation.

## Failure behaviour

| Failure | Behaviour |
| :--- | :--- |
| Kafka down | Polling fallback, alert |
| Mercury API slow | Backpressure, queue grows, alert at 5,000 |
| Marketplace rate limited | Backoff honoured, per-channel quota |
| Orbit unreachable | EDI and store files queue; no customer impact until the next window |

## Related

[Integration landscape](../../current-state/systems/integration-landscape.md) ·
[Marketplace stock display](../../current-state/channels/marketplaces.md) ·
[Event flows](../event-flows.md)
