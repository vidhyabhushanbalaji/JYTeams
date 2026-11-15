# Decision Records

Status: Agreed · Owner: Nadia Kerr · Last updated: 2026-11-13

Ten decisions that shape the platform, each with the options that were rejected. A decision record
without its alternatives is just a description, so every file here says what we did **not** do and why.

## The records

| ID | Decision | Date | Status |
| :--- | :--- | :--- | :--- |
| [0001](./0001-reserve-stock-at-payment-authorisation.md) | Reserve at payment authorisation, not at basket | 2026-10-22 | Accepted |
| [0002](./0002-event-driven-stock-updates.md) | Event-driven stock updates, not polled snapshots | 2026-10-09 | Accepted |
| [0003](./0003-single-availability-service.md) | One availability service, one formula | 2026-09-24 | Accepted |
| [0004](./0004-poll-marketplace-inventory.md) | Push marketplace inventory every five minutes | 2026-10-16 | Accepted |
| [0005](./0005-carrier-api-for-delivery-promise.md) | Carrier APIs for the date, not a lead-time table | 2026-09-30 | Accepted |
| [0006](./0006-redis-cache-with-short-ttl.md) | Redis cache with a 60-second TTL | 2026-10-09 | Accepted |
| [0007](./0007-store-collection-uses-store-stock.md) | Store collection uses store stock, not warehouse stock | 2026-10-23 | Accepted |
| [0008](./0008-retain-mercury-as-order-system.md) | Keep Mercury as the order system | 2026-09-18 | Accepted |
| [0009](./0009-per-channel-cutover.md) | Cut over per channel, not all at once | 2026-10-30 | Accepted |
| [0010](./0010-conservative-fallback-promise.md) | Fall back to a range, never to a guessed date | 2026-11-06 | Accepted |

## How a record is written

| Section | Contains |
| :--- | :--- |
| Status | Proposed, accepted, superseded, with a date |
| Context | The problem, with the numbers that made it a problem |
| Options | At least two real alternatives, with the reason each was rejected |
| Decision | One sentence, in the active voice |
| Consequences | What becomes harder, not only what becomes easier |

The consequences section is the one that gets skipped and the one that matters. Every decision here
has costs, and they are written down so that a future team can see what they are inheriting.

## What is not an ADR

Configuration changes (in [policy configuration](../reservation-policy/specification/policy-configuration.md)),
test approach, and vendor selection below £25 k. Those are decisions, but they are not architectural,
and a decision log that records everything records nothing.

## Superseding

A decision is superseded, never edited. The old record keeps its context and its status changes, so the
reasoning at the time remains readable. Two records already reference each other: 0002 changed how 0006
was applied, and 0009 constrains how 0003 is deployed.

## Related

[Architecture](../architecture/) · [Steering decisions](../programme/governance/steering-group.md) ·
[Decision rights](../programme/governance/decision-rights.md)
