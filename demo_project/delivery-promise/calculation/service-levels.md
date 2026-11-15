# Service Levels

Status: Agreed · Owner: Gavin Shore · Last updated: 2026-11-06

What we actually sell to a customer, what it costs, and what each service implies for the promise.
Marketing names are deliberately kept out of this document: the promise is built on the operational
service, and the two are mapped in one place.

## The services

| Operational service | Customer-facing name | Lead time | Price | Available to |
| :--- | :--- | :--- | :--- | :--- |
| `parcel_next_day` | Next Day | 1 working day | £4.95, free over £60 | Parcels only |
| `parcel_saturday` | Saturday Delivery | Saturday | £6.95 | Parcels, 41 postcodes excluded |
| `parcel_two_day` | Standard | 2 working days | £3.95, free over £40 | Parcels |
| `locker_24h` | Collect from a locker | 1 working day | £2.95 | Parcels under 45 cm |
| `bulky_two_person` | Room of Choice | 3–5 working days | £19.95, free over £500 | Bulky |
| `bulky_named_day` | Choose Your Day | 3–7 working days | £29.95 | Bulky with slots |
| `bulky_assembly` | Delivered and Assembled | 5–7 working days | £49.95 | Selected products |
| `collection` | Collect from store | Ready next day | Free | Stores with stock |

## How the service is chosen

The customer picks a service at checkout, but the platform filters the list first. A service appears
only when all of the following are true:

1. The postcode is serviceable for it.
2. A warehouse can serve the whole order on that service's cut-off.
3. The parcel meets size and weight limits.
4. The product is not excluded (age-restricted, hazardous, personalised).
5. The date it implies is inside the horizon (14 days for bulky).

Filtering before display is a change from today, where all options are shown and some are withdrawn
after payment. That withdrawal was **2.6 % of orders** in September and produced 1,100 contacts.

## Free delivery thresholds

| Basket value | Standard | Next Day | Bulky |
| :--- | :--- | :--- | :--- |
| Under £40 | £3.95 | £4.95 | £19.95 |
| £40–£59.99 | Free | £4.95 | £19.95 |
| £60+ | Free | Free | £19.95 |
| £500+ | Free | Free | Free |

Thresholds are commercial and change without platform work, because price is not part of the promise
calculation. The service *availability* is, and that does change with the warehouse and the postcode.

## What we do not offer

| Service | Why not |
| :--- | :--- |
| Sunday delivery | Carrier cost, 14 % uptake in a 2025 trial |
| Same-day | Only feasible inside the M25; a London pilot is being considered for 2027 |
| Timed slots for parcels | Parcelway cannot guarantee a window |
| Delivery to a different address after dispatch | Fraud and carrier rules |
| International | Not in scope; a separate programme |

## Service level and promise accuracy

The promise is most accurate on the shortest service, because fewer things can go wrong:

| Service | Promise accuracy today | Target |
| :--- | :--- | :--- |
| Next Day | 84 % | 96 % |
| Standard | 79 % | 94 % |
| Locker | 91 % | 97 % |
| Bulky | 58 % | 88 % |
| Collection | 68 % | 88 % |

The bulky and collection targets are lower on purpose. Promising 96 % for a two-person delivery on a
capacity-constrained network would be a promise to the steering group that the carriers cannot keep.

## Related

[Delivery date logic](./delivery-date-logic.md) · [Carrier performance](../carriers/carrier-performance.md) ·
[Promise accuracy](../customer-messaging/promise-accuracy.md)
