# Reservation Events

Status: Draft · Owner: Nadia Kerr · Last updated: 2026-11-13

Every change to a reservation is published as an event. Events are the only way other systems learn
about a reservation, and the only way an incident can be reconstructed after the fact.

## Topics

| Topic | Published by | Key | Retention |
| :--- | :--- | :--- | :--- |
| `reservation.created` | Reservation worker | `sku` | 7 days |
| `reservation.allocated` | Reservation worker | `sku` | 7 days |
| `reservation.released` | Reservation worker | `sku` | 7 days |
| `reservation.expired` | Expiry job | `sku` | 7 days |
| `stock.changed` | Feed ingestor | `sku` | 24 hours |
| `order.placed` | Mercury adapter | `order_id` | 7 days |

Partitioning by `sku` is deliberate: two events for the same SKU are ordered, which is what makes
concurrent reservations safe. Events for different SKUs may arrive in any order.

## Envelope

| Field | Type | Purpose |
| :--- | :--- | :--- |
| `event_id` | UUID | Idempotency for consumers |
| `event_type` | string | Matches the topic |
| `occurred_at` | ISO 8601 UTC | When the change happened, not when it was published |
| `published_at` | ISO 8601 UTC | When it hit the bus |
| `schema_version` | integer | 1 for this release |
| `correlation_id` | UUID | The order or feed batch that caused it |
| `payload` | object | Type-specific |

## Payloads

### `reservation.created`

| Field | Example |
| :--- | :--- |
| `reservation_id` | `01HQ7…` |
| `order_id` | `MH-4821993` |
| `line_id` | `2` |
| `sku` | `HH-GDP-4410` |
| `quantity` | `1` |
| `location` | `midlands-dc` |
| `mode` | `soft` |
| `expires_at` | `2026-11-13T10:41:22Z` |

### `reservation.released`

Adds `reason_code` and `released_by`. The reason is mandatory: a release without a reason fails
validation and goes to the dead-letter topic, which is intentional. A silent release is the failure
mode this platform exists to remove.

### `stock.changed`

Carries `sku`, `location`, `available`, `quarantine`, `allocated`, `feed_timestamp` and
`feed_sequence`. Consumers must ignore an event whose `feed_sequence` is older than the one they
have already applied.

## Delivery guarantees

| Guarantee | Detail |
| :--- | :--- |
| At-least-once | Consumers must be idempotent on `event_id` |
| Ordering | Per SKU only |
| Schema | Validated against the registry at publish; invalid messages rejected |
| Dead letters | `reservation.dlq`, alerted after 5 messages in 10 minutes |
| Replay | 7 days by offset, or by `order_id` from the archive |

## What is not an event

Stock snapshots are not events. A full warehouse snapshot is a state transfer, written to the
ingestor's store and published as a `stock.changed` per changed SKU only. Publishing every record
of a 210,000-row snapshot would be 210,000 events per cycle for maybe 400 real changes.

## Related

[Event flows](../../architecture/event-flows.md) · [Reservation lifecycle](../policy/reservation-lifecycle.md) ·
[Feed message data dictionary](../../reference/data-dictionary/feed-message.md)
