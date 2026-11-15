# Basket and Checkout

Status: In draft · Owner: Tom Alder · Last updated: 2026-11-13

The basket has to answer a question the product page could not: **when will this whole order
arrive?** For a split order the honest answer is two dates, and getting that right is the change
customers notice most.

## Basket

| Element | Behaviour |
| :--- | :--- |
| Per-line date | Each line shows its own shipment date |
| Grouped shipments | Lines grouped by warehouse and service, max 3 groups |
| Headline | The latest shipment date, with "arrives in 2 deliveries" when split |
| No date | "Date unavailable" on the line, headline shows the latest known date |
| Mixed basket | Bulky and parcel produce two groups with different services |

A basket with one bulky item and one parcel shows:

```text
Garden bench            Delivered 28 May – 2 June (two-person)
Cushion cover           Delivered Thu 20 May (next day)
Arrives in 2 deliveries
```

The bulky range is a range because the slot is not booked until the order exists. That inconsistency
is visible to customers and is the strongest argument for the slot-aware promise once RSV-06 is
decided.

## Checkout

Checkout filters services by availability rather than offering everything, which is the biggest
behavioural change from today.

| Step | What happens |
| :--- | :--- |
| Address entered | Postcode lookup, serviceability resolved |
| Services shown | Only serviceable services, each with its date and price |
| Store collection | Offered when a store within 20 miles has stock |
| Delivery group summary | Number of deliveries, dates, no split cost |
| Payment | Reservation created on authorisation |

## Why services are filtered, not disabled

Disabling an unserviceable option keeps it visible and explains why it is unavailable; filtering hides
it. Customer testing in December will compare the two, because there is a real argument that seeing
"Saturday delivery unavailable for this postcode" is better than not seeing Saturday at all. The
default is filtering, with a link explaining restrictions.

## Postcode lookup

The address step calls the serviceability endpoint once per postcode change, not per keystroke, and
caches the result for the session. The lookup also returns the store options, because a customer who
cannot get next-day is the customer most likely to collect.

## Failure behaviour

| Failure | Checkout shows |
| :--- | :--- |
| Serviceability API down | Standard delivery, 3–5 days, labelled as an estimate |
| No serviceable service | Collection only, or a contact-us message |
| Reservation fails at payment | Payment not taken; retry with a clear message |
| Reservation expires during payment | One retry, then an apology and a fallback date |

The fourth case is the one to watch in UAT: a slow 3-D Secure challenge can outlast a 30-minute
reservation, and the retry path has to be tested with a deliberately slow sandbox response.

## Abandonment

| Change | Effect measured in September trial |
| :--- | :--- |
| Date on the basket | +2.1 % conversion |
| Grouped deliveries | −11 % "where is my order" contacts |
| Filtered services | −0.4 % conversion, +3.2 % satisfaction |
| Countdown on the product page | +1.4 % conversion |

The filtered-services change costs a small amount of conversion and was accepted anyway, because the
alternative is collecting money for a service we then withdraw.

## Related

[Product page messaging](./product-page-messaging.md) · [Postcode lookup](./postcode-lookup.md) ·
[Delivery date scenarios](../../customer-testing/test-cases/delivery-date-scenarios.md)
