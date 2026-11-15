# Fallback Messaging

Status: Draft · Owner: Tom Alder · Last updated: 2026-11-13

When the platform cannot compute a date, the customer still needs to be told something. The fallback
is a five-day estimate, shown only when no defensible date exists, and it is the only place we use a
range.

## When the fallback appears

| Condition | Fallback used |
| :--- | :--- |
| Availability stale for every warehouse serving the SKU | Yes |
| DPS unavailable | Yes |
| Carrier serviceability unavailable | Yes |
| No serviceable service | No: collection or "cannot deliver" |
| Out of stock | No: notify me |
| Pre-order | No: release date |

## The copy

| Surface | Copy |
| :--- | :--- |
| Product page | "Delivery date unavailable right now — order today and we will confirm within 24 hours." |
| Basket | "Delivery date to be confirmed" |
| Checkout | "Standard delivery, 3–5 working days. We will confirm your date within 24 hours." |
| Confirmation email | "We are confirming your delivery date and will email you within 24 hours." |
| Order tracking | "Date pending confirmation" |

The phrase "3–5 working days" is deliberately the same phrase the contact centre already uses, so an
agent and the website do not contradict each other.

## Why not a best-guess date

A wrong specific date is worse than an honest estimate. The contact centre interview is explicit
about this: customers forgive "three to five days" and do not forgive a broken Thursday. The promise
accuracy metric counts a fallback order as **not promised**, so a fallback never flatters the number.

## Legal review (DEP-08)

Leah Okafor and legal are reviewing three points:

| Point | Concern | Proposed resolution |
| :--- | :--- | :--- |
| "We will confirm within 24 hours" | Creates a contractual commitment to communicate | Commit to 24 hours during working days only |
| "3–5 working days" vs the service sold | The customer may have paid for next-day | Refund the service difference automatically |
| No date at all at checkout | Consumer distance-selling rules require a delivery timeframe | Show 3–5 working days as the timeframe |

The third point is why the fallback is a range at all: showing nothing is a legal problem, not just a
user-experience one.

## How often it happens

| Period | Fallback share | Cause |
| :--- | :--- | :--- |
| October 2026 baseline | 4.1 % | Stale feeds and missing dates |
| Target at launch | ≤ 1.0 % | Five-minute feeds, computed dates |
| Acceptable during an incident | ≤ 10 % | Degraded platform |

Every fallback is logged with a reason, and the daily operations report breaks them down. A rise in
fallback share is the earliest signal that something upstream has broken, often before an alert
fires.

## What agents see

The contact centre screen shows the same date or fallback text the customer saw, plus the reason.
That is a small change with a large effect: previously agents had a Mercury date that disagreed with
the website and had to guess which to trust.

## Related

[Unavailable dates](../calculation/unavailable-dates.md) · [ADR 0010](../../decisions/0010-conservative-fallback-promise.md) ·
[Contact centre interview](../../current-state/interviews/contact-centre-interview.md)
