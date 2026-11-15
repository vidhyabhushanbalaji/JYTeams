# Architecture

Status: Draft · Owner: Nadia Kerr · Last updated: 2026-11-13

Four new services, one event bus, two data stores, and a deliberate decision to leave Mercury and
Horizon alone. This folder describes how the platform is built and why it is built that way.

## The principles

1. **One availability computation.** Anywhere the same question is asked, the same function answers
   it. The quarantine bug (INC-005) came from three implementations of one formula.
2. **Business rules are configuration.** Rules change; a deployment to change a 30-minute window is a
   design failure.
3. **Fail visibly, not creatively.** A missing date is acceptable; an invented one is not.
4. **Every change has a reason.** Reservations, releases and holds all carry one.
5. **Leave the legacy where it is.** Mercury routes, Horizon accounts; changing either is a different
   programme.

## The components

| Component | Responsibility | Store |
| :--- | :--- | :--- |
| [Stock feed ingestor](./services/stock-feed-ingestor.md) | Poll, validate, normalise, publish | Postgres (snapshots) |
| [ATP service](./services/atp-service.md) | Availability and quotes | Postgres, Redis |
| [Reservation worker](./services/reservation-worker.md) | Reservation state machine | Postgres |
| [Delivery promise service](./services/delivery-promise-service.md) | The date | Postgres, Redis |
| [Integration hub](./services/integration-hub.md) | Order and dispatch events, Orbit bridging | Kafka |
| Kafka `truestock-events` | Event backbone | — |

## The stores

| Store | Holds | Retention |
| :--- | :--- | :--- |
| Postgres | Stock snapshots, reservations, promises, configuration | 90 days rolling, promises 30 days |
| Redis | Availability cache, serviceability cache, rate limits | TTL 60 s to 24 h |
| Object storage | Feed batches, replay fixtures, evidence | 30 days |

## Read this in order

| If you want | Read |
| :--- | :--- |
| The shape of the system | [Overview](./overview.md) |
| Who talks to what | [System context](./system-context.md) |
| Tables and fields | [Data model](./data-model.md) |
| What happens when an order arrives | [Event flows](./event-flows.md) |
| One service in detail | [Services](./services/) |
| SLOs, security, environments | [Platform](./platform/) |

## What is deliberately boring

No microservice per warehouse, no CQRS, no event sourcing, no service mesh. Four services and a queue
is enough for 25 events per second, and every extra pattern is something the two-person platform team
would have to operate at 02:00.

## What is deliberately unusual

| Choice | Reason |
| :--- | :--- |
| Redis snapshot cache with a 60-second TTL | 420 reads per second against Postgres was wasteful, not impossible |
| Availability computed on write, not on read | Read latency had to be under 40 ms |
| Promise records stored | Accuracy is measured against what we said, not what we would say now |
| Conservative fallback as a first-class state | The 71 % baseline shows guessing is worse |

## Related

[ADR 0002](../decisions/0002-event-driven-stock-updates.md) · [ADR 0003](../decisions/0003-single-availability-service.md) ·
[Platform](./platform/environments.md)
