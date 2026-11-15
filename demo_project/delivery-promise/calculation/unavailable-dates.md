# Unavailable Dates

Status: Agreed · Owner: Tom Alder · Last updated: 2026-11-06

The cases where we deliberately show no date. They are the hardest part of the customer messaging,
because "we cannot tell you" is a worse experience than a slightly wrong date in the short term and a
much better one in the long term.

## The eight cases

| Case | Condition | What the customer sees |
| :--- | :--- | :--- |
| Not serviceable | Postcode outside every carrier's network | Collection offered, or "we cannot deliver here" |
| Out of stock | No availability at any warehouse | "Notify me" or collection from a store |
| Stale stock | Every contributing feed past its threshold | "Delivery date unavailable right now" |
| Outside the horizon | Bulky beyond 14 days | "Week commencing …" |
| Capacity exhausted | Carrier cap reached for the day | Standard service offered instead |
| Restricted product | Age, hazard or personalisation rules | Collection only |
| Degraded platform | DPS or ATP unavailable | Fallback estimate, labelled |
| Basket too large | Over 40 lines or over carrier limits | Multiple deliveries, no combined date |

## What each looks like

### Not serviceable

Scottish islands and parts of the Highlands for next-day, and 1.9 % of postcodes for bulky. The
message names the alternative rather than simply failing: "Two-day delivery available" or "Collect
from Oban". Today the site silently removes options, which is why customers choose a service that
then disappears.

### Stale stock

The most operationally likely case. The message is deliberately vague about cause and specific about
consequence: "We cannot confirm a delivery date right now. Order now and we will confirm within 24
hours." It must never say "system error", which invites a support call.

### Outside the horizon

Bulky is the only service with a hard horizon, because Northline's slot API only looks 14 days ahead.
Beyond that the promise is a week: "Week commencing 8 June". Weeks are acceptable; invented days are
not.

### Capacity exhausted

Rare and new: when a carrier cap is reached, next-day is withdrawn for the day rather than promised
and missed. This requires the daily capacity figure described in the peak calendar, and until it is
automated it is a manual hold.

### Degraded platform

If DPS is down, the fallback is a 5-day estimate from configuration (`promise.fallback_days`), shown
with the caveat "may arrive sooner". The wording is with legal for review (DEP-08), because it is the
one place we show an estimate rather than a date.

## What we never do

| Never | Why |
| :--- | :--- |
| Show today's date for an unfulfillable order | Guarantees a missed promise |
| Show a date and withdraw it after payment | 2.6 % of orders, 1,100 contacts in September |
| Show a range for a specific service | Ranges are only for the fallback |
| Hide the fact that a date is uncertain | The customer finds out anyway, by phone |
| Promise a date for stock in quarantine | The unit is not sellable |

## Measuring unavailability

| Metric | Target | Why |
| :--- | :--- | :--- |
| Orders with no date | ≤ 3 % | Higher means the feeds or carriers are failing |
| Orders with fallback estimate | ≤ 1 % | Higher means the platform is degraded |
| Withdrawn services after payment | 0 | A design goal, not an aspiration |
| Contacts caused by a missing date | ≤ 200/day | Contact centre capacity |

Every case of "no date" is logged with the reason, which is what makes the first two metrics
possible and what tells the operations team which feed to fix first.

## Related

[Delivery date logic](./delivery-date-logic.md) · [Fallback messaging](../customer-messaging/fallback-messaging.md) ·
[Product page messaging](../customer-messaging/product-page-messaging.md)
