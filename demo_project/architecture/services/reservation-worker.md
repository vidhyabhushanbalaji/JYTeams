# Reservation Worker

Status: Draft · Owner: Nadia Kerr · Last updated: 2026-11-13

Owns the reservation state machine. It is the only component allowed to write a reservation, which is
the control that makes "reserve once, release with a reason" enforceable rather than aspirational.

## Responsibilities

| Does | Does not |
| :--- | :--- |
| Consume `order.placed` | Compute availability (asks ATP) |
| Create, allocate, release, expire | Compute dates (asks DPS) |
| Enforce the policy rules | Let any caller set a state |
| Publish reservation events | Touch warehouse systems directly |

## State machine

```text
             ┌──────────┐   expire    ┌─────────┐
order.placed │   soft   │────────────▶│ expired │
             └────┬─────┘             └─────────┘
                  │ allocate (warehouse)
                  ▼
             ┌──────────┐  dispatch   ┌────────────┐
             │allocated │────────────▶│ dispatched │
             └────┬─────┘             └────────────┘
                  │ cancel / reject
                  ▼
             ┌──────────┐
             │ released │◀── cancel (from soft)
             └──────────┘
```

## Work on `order.placed`

1. Read the order lines and the split shipment grouping.
2. Ask ATP for availability per line.
3. Apply the rules: RSV-01, RSV-06 if decided, RSV-12 for staleness, RSV-20 for partials.
4. Create reservations atomically per shipment, or none if any line fails and partial was not allowed.
5. Ask DPS for a promise per shipment.
6. Publish `reservation.created` and `promise.issued`.

## Idempotency

| Key | Effect |
| :--- | :--- |
| `(order_id, line_id, attempt)` | A repeat returns the existing reservation |
| Event `event_id` | Duplicate events ignored |
| Batch replay | Safe; state transitions are guarded by current state |

An order event delivered twice must not create two reservations. The database constraint enforces
this, not the application logic alone, because a race between two consumers is exactly the scenario
that produced seven double-claims in a rehearsal.

## Expiry

| Property | Value |
| :--- | :--- |
| Sweep interval | 60 s |
| Soft TTL | 1800 s, 3600 s after capture |
| Offset from wave window | 10 s |
| Batch size | 500 per sweep |

The offset exists because expiring during a wave build produced double-claims in UAT.

## Concurrency

| Concern | Handling |
| :--- | :--- |
| Two orders, one unit | Atomic conditional insert; one wins |
| Duplicate order event | Unique constraint |
| Release during allocate | State guard; last valid transition wins |
| Worker restart mid-order | Event replay from the last committed offset |

## Failure behaviour

| Failure | Behaviour |
| :--- | :--- |
| ATP unavailable | Retry with backoff, then order flagged without a promise |
| DPS unavailable | Reservation stands, promise flagged as fallback |
| Kafka consumer lag | Alert at 30 s lag |
| Database down | No reservations; the site keeps selling until stale guard bites |

The fourth row is the one to fear: if reservations stop for 15 minutes, the stale guard is the only
thing between us and a wave of oversells. That is why consumer lag alerts at 30 seconds.

## Metrics

| Metric | Alert at |
| :--- | :--- |
| Consumer lag | 30 s |
| Reservation success rate | Below 99 % |
| Expiry sweep duration | Above 10 s |
| Failed transitions | Any |

## Related

[Reservation lifecycle](../../reservation-policy/policy/reservation-lifecycle.md) ·
[Reservation rules](../../reservation-policy/policy/reservation-rules.md) ·
[Event flows](../event-flows.md)
