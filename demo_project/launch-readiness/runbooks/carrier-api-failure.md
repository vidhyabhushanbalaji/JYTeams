# Runbook — Carrier API Failure

**Symptom:** checkout shows no services, or a single service disappears; bookings fail; tracking stops
updating.

**Customer impact:** depends on where it fails. A serviceability failure removes options; a booking
failure stops dispatch. The second is much worse and usually appears hours later.

## 1. Which call failed (2 minutes)

| Call | Endpoint | Failure looks like |
| :--- | :--- | :--- |
| Serviceability | `GET /v2/serviceability` | No delivery options at checkout |
| Booking | `POST /v2/consignments` | Orders with no label, stuck before dispatch |
| Tracking | `GET /v2/tracking/{id}` | No dispatch confirmation, customer asks |
| Cancel | `DELETE /v2/consignments/{id}` | Cancelled orders still collected |

Booking failures are the urgent ones. Check the queue first:

| Check | Where |
| :--- | :--- |
| Booking queue depth | Integration dashboard, per carrier |
| Oldest queued booking | Same panel |
| Failed bookings in the last hour | `carrier_booking_failures` |

## 2. Immediate actions by failure

| Failure | Action |
| :--- | :--- |
| Serviceability down | Serve the cached district response; do not disable checkout |
| Booking down | Queue bookings; do not fail the order |
| Tracking down | Nothing customer-facing; support uses the carrier portal |
| Cancel down | Log it; the carrier will collect, and the refund is manual |
| All calls down | Withdraw the affected services from checkout; other carriers continue |

Withdrawing a service is a configuration change, not a deployment: toggle in the admin console, takes
effect within one minute.

## 3. Check the carrier's side (3 minutes)

1. Carrier status page.
2. Rate limit response headers (`429` means throttle, not outage).
3. Sandbox versus production credentials: a credential rotated on their side looks exactly like an
   outage.
4. Named contact: call them, do not email.

## 4. What to tell customers

| Situation | Message |
| :--- | :--- |
| Next-day withdrawn | "Next-day is temporarily unavailable; standard delivery is available" |
| Booking delayed | Nothing yet; the promise may still be met |
| Tracking missing | "Your order is on its way; tracking may be delayed" |

Never say "carrier problem". The customer's contract is with us.

## 5. Recovery

- [ ] Queue drains without duplicate bookings
- [ ] Any failed booking re-attempted with the same idempotency key
- [ ] Serviceability back to normal option set
- [ ] Tracking caught up for the affected window
- [ ] Affected orders identified and checked against their promise

## 6. The 24-hour check

| Check | Why |
| :--- | :--- |
| Every order from the window has a label | Some failures are silent |
| Promised dates still achievable | A booking delay can break a promise without any error |
| Rebookings and their cost | Northline rebookings are £46 each |

The second item is the one that gets missed: a carrier outage that resolves in 40 minutes can still
mean 200 orders miss their promise, and those customers need telling.

## Escalation

| Time | Who |
| :--- | :--- |
| 0 min | On-call |
| 15 min | Gavin Shore |
| 30 min | Marcus Feld if bookings are failing |
| 60 min | Priya Raman if a channel is affected |

## Never do

| Never | Why |
| :--- | :--- |
| Re-book without the idempotency key | Duplicate labels and duplicate charges |
| Switch carriers silently | Different promise, different tracking link, confused customers |
| Promise a date "because the carrier is back" | Their backlog is not your capacity |
| Delete queued bookings | They are the record of what is owed |

## Related

[Carrier onboarding](../../delivery-promise/carriers/carrier-onboarding.md) ·
[Postcode lookup](../../delivery-promise/customer-messaging/postcode-lookup.md) ·
[Rollback triggers](../rollback/rollback-triggers.md)
