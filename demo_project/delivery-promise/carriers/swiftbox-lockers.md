# Swiftbox Lockers

Status: In review · Owner: Gavin Shore · Last updated: 2026-11-06

Swiftbox is our locker network: 4,100 lockers, 88 % of the population within one mile, 24–48 hour
delivery. It is cheap, popular with customers under 35, and completely unsuitable for anything larger
than a shoebox, which is most of what we sell.

## Service summary

| Property | Value |
| :--- | :--- |
| Lockers | 4,100 sites |
| Coverage | 88 % of UK population within 1 mile |
| Lead time | 24 hours to locker, 48 hours in the Highlands |
| Maximum size | 45 × 35 × 25 cm |
| Maximum weight | 15 kg |
| Hold period | 5 days, then returned to depot |
| Cut-off | 16:00 |
| Share of orders | 7 % |

## What fits

| Product group | Fits | Note |
| :--- | :--- | :--- |
| Cushions, throws, textiles | Yes | The main use case |
| Small kitchenware | Yes | Box volume permitting |
| Candles and gifting | Yes | — |
| Vases and ceramics | Some | Fragile handling surcharge |
| Anything over 45 cm | No | Forced to Parcelway |
| Bulky | No | Forced to Northline |

The size check is done from Atlas dimensions, and **382 SKUs** have no recorded dimensions, so the
site cannot offer a locker for them. Filling those dimensions is an Atlas data task, not a platform
task, and it is on the merchandising backlog.

## Why it matters to the promise

Locker delivery is the cheapest service we offer (£2.14 per parcel) and the most predictable, because
it does not depend on the customer being at home. Two consequences:

1. Where a locker is available, it is the recommended option in checkout, and recommendation order
   affects conversion measurably (+1.8 % in a September trial).
2. The promise for a locker is 24 hours, which is often earlier than next-day to a home address in
   the same postcode, so the delivery-date logic must compare services rather than assume the fastest
   is next-day.

## Integration

| Capability | Endpoint | Notes |
| :--- | :--- | :--- |
| Locker search by postcode | `GET /lockers?postcode&radius` | Returns sites with size classes |
| Availability | `GET /lockers/{id}/capacity` | Real time, refreshed per booking |
| Book | `POST /parcels` | Locker ID plus parcel dimensions |
| Label | `GET /parcels/{id}/label` | 4×6 PDF |
| Collection events | Webhook | Collected, expired, returned |

The capacity endpoint is genuinely real time, which makes Swiftbox the only carrier where the
promise can be certain rather than indicative. It is also the only carrier whose capacity feed we
consume at all, and that asymmetry is worth remembering when the bulky slot problem is discussed.

## Constraints

| Constraint | Effect |
| :--- | :--- |
| One locker per parcel | A two-item order becomes two parcels to two lockers; customers dislike it |
| No age or ID verification | Excluded categories stay excluded |
| Customer has 5 days | Return-to-depot handling costs £3.10 |
| Rollout paused in Scotland | 41 new sites planned for 2027 |

## Related

[Carrier onboarding](./carrier-onboarding.md) · [Basket and checkout](../customer-messaging/basket-and-checkout.md) ·
[Carrier performance](./carrier-performance.md)
