# Carrier Onboarding

Status: Agreed · Owner: Gavin Shore · Last updated: 2026-11-06

Adding a carrier to the platform takes about ten weeks and has seven gates. The process exists
because a carrier added badly produces a promise we cannot keep, and the carrier gets blamed for it.

## The gates

| Gate | What must be true | Owner | Typical time |
| :--- | :--- | :--- | :--- |
| 1. Commercial | Rates, volume commitment, service levels agreed | Gavin Shore | 3 weeks |
| 2. Serviceability | Postcode, size, weight and exclusion rules documented | Gavin Shore | 1 week |
| 3. API access | Sandbox credentials, rate limits and error codes known | Dan Whitcombe | 2 weeks |
| 4. Integration | Serviceability, booking, tracking and cancel implemented | Nadia Kerr | 3 weeks |
| 5. Promise rules | Lead times, cut-offs and calendar encoded and tested | Gavin Shore | 1 week |
| 6. Operations | Label format, collection time, escalation path agreed | Marcus Feld | 1 week |
| 7. Launch | Pilot on one warehouse at low volume, then all | Gavin Shore | 1 week |

Gates cannot be run in parallel except 1 with 2, and 4 with 6. Every carrier we have added in a hurry
has skipped gate 5 and produced dates that were wrong for a fortnight.

## What a carrier must provide

| Item | Why |
| :--- | :--- |
| Serviceability API or machine-readable zone file | The promise cannot be computed from a PDF |
| Booking API with idempotency | Duplicate bookings cost money twice |
| Tracking webhook or a reliable poll | Dispatch confirmation and customer messaging |
| Cancellation API | Releases and rebooks |
| Documented error taxonomy | Retry decisions |
| Named technical contact | During hypercare |
| Test parcels accepted | Labels and scanning verified end to end |

A carrier without an API is not onboarded. That rule costs revenue occasionally and has saved at
least one disastrous launch.

## Pre-launch checklist

- [ ] Serviceability tested against 200 postcodes, including islands and one BT block
- [ ] Booking tested with a duplicate request
- [ ] Cancel tested before and after collection scan
- [ ] Label printed on the label printer the warehouse actually uses
- [ ] Tracking events received for three test parcels
- [ ] Cut-off confirmed in writing by the carrier's operations team
- [ ] Promise rules tested against the delivery-date logic test suite
- [ ] Contact centre briefed on the new service name and tracking link
- [ ] Carrier added to the escalation matrix in the hypercare plan

## Who is next

Three carriers are in discussion for 2027: a same-day courier for London (pilot only), a second
two-person network to relieve Northline's Scotland capacity (R-06), and a returns carrier. None is in
scope for the May launch, and all must go through these gates rather than being bolted on.

## Related

[Carrier performance](./carrier-performance.md) · [Service levels](../calculation/service-levels.md) ·
[Rollback plan](../../launch-readiness/rollback/rollback-plan.md)
