# Known Failures

Status: Agreed · Owner: Dan Whitcombe · Last updated: 2026-11-06

The eight ways the current order-to-warehouse path fails, with frequency and cost. Each one is
referenced by at least one design decision, so this document is the evidence base for the
programme's priorities rather than a complaint list.

## The failure catalogue

| ID | Failure | Frequency | Customer impact | Root cause |
| :--- | :--- | :--- | :--- | :--- |
| F-01 | Oversell: order accepted, no stock to pick | 300/day (2.1 %) | Cancellation or substitution | Stock data 30 min to 14 h old |
| F-02 | Phantom stock: system says stock, shelf is empty | 190/day | Late cancellation | Adjustments and theft not reflected |
| F-03 | Split shipment not predicted | 38 % of orders | Unexpected second parcel, no date | Split decided after routing |
| F-04 | Stuck order in `pending` for more than 6 hours | 40/day | Customer calls, late dispatch | Orbit dead-letter not monitored |
| F-05 | Amazon pending order treated as confirmed | 11 in October | Stock held for a non-order | ChannelBridge status mapping |
| F-06 | Store says "in stock", collection cancelled | 18 % of collection orders | Wasted trip, refund | Nightly store file plus 91 % accuracy |
| F-07 | Promise missed on bulky items | 42 % of bulky orders | Rescheduled delivery, redelivery cost | Carrier booking not linked to stock |
| F-08 | Dispatch confirmation not sent to marketplace | 26 in October | Account health warning | Tracking upload retried manually |

## What the failures cost

| Failure | Direct cost per month | How measured |
| :--- | :--- | :--- |
| F-01 Oversell | £38,000 in refunds and goodwill | Contact centre credits, October |
| F-02 Phantom stock | £21,000 | Same |
| F-03 Split surprise | £9,000 in duplicate carriage | Carrier invoices |
| F-06 Collection cancellations | £14,000 | Refunds plus travel vouchers |
| F-07 Bulky misses | £31,000 in redelivery | Northline invoices |
| F-08 Marketplace defects | Not quantifiable | Account health, risk only |

Total quantifiable cost is **£113,000 a month**, against a programme cost of £1.41 m, which is the
single strongest argument for the programme and the one used in the original business case.

## Common thread

F-01, F-02, F-03 and F-06 are all the same failure: a decision made on stock data that is not
current, by a system that cannot ask for better data. Fixing the feed and the reservation makes
those four visible but not automatically fixed; the promise also has to stop making claims it
cannot keep, which is why delivery promise is a separate workstream with its own accuracy metric.

F-04 and F-05 are integration defects that a monitored event stream would surface in minutes
instead of days. F-07 is a carrier booking problem, not a stock problem.

## How this drives the design

| Failure | Design response |
| :--- | :--- |
| F-01, F-02 | [Reservation policy](../../reservation-policy/policy/oversell-prevention.md), stale thresholds |
| F-03 | Availability by warehouse, split prediction at checkout |
| F-04, F-05 | Event stream with dead-letter alerting, see [observability](../../architecture/platform/observability.md) |
| F-06 | Store reservation, hourly store feed |
| F-07 | Carrier booking API inside the promise calculation |
| F-08 | Dispatch events from Mercury, tracking upload retried by the integration hub |

## Related

[Manual interventions](./manual-interventions.md) · [Oversell prevention](../../reservation-policy/policy/oversell-prevention.md) ·
[Promise accuracy](../../delivery-promise/customer-messaging/promise-accuracy.md)
