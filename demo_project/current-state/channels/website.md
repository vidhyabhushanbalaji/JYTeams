# Website Channel

Status: Agreed · Owner: Ruth Iyer · Last updated: 2026-10-28

`harbourandheath.com` is our largest channel: 7,400 orders a day, 52 % of total volume, average
order value £68. The storefront runs on Shopify Plus with our own checkout wrapper, and stock is
shown as a binary "in stock" flag driven by a nightly Mercury extract.

## How an order is made

1. Customer adds to basket. No stock is checked or held at this point.
2. Checkout calls `HHCheckout`, our wrapper, for payment and address validation.
3. On payment success, Shopify emits an `orders/create` webhook.
4. Orbit receives the webhook and writes an order into Mercury, typically within 8 seconds.
5. Mercury routes the order overnight, or immediately if it is flagged as next-day.

## What the customer sees

| Element | Today | Under Truestock |
| :--- | :--- | :--- |
| Product page | "In stock" or "Out of stock" | Stock state plus a delivery date |
| Basket | Nothing | Earliest promised date per item |
| Checkout | Shipping options by value band | Carrier options filtered by stock location |
| Confirmation | "We will email you" | Committed date range, per shipment |

There is no quantity displayed anywhere on the site, deliberately: the merchandising team has
argued since 2023 that "only 2 left" damages conversion on considered purchases. That argument is
still open and CR-008 was rejected for this release.

## Where it breaks

| Symptom | Cause | Frequency |
| :--- | :--- | :--- |
| Item shown in stock, cancelled after order | Stock flag up to 14 hours old | ~310 orders/week |
| Delivery option offered that the warehouse cannot meet | Carrier options are value-based, not stock-based | ~180 orders/week |
| Customer sees one delivery, receives two parcels | Split shipment not predicted at checkout | 38 % of multi-item orders |

## Stock display rules today

The flag is true when Mercury's `available` figure for the product is above the safety buffer of
five units. The buffer exists because the nightly extract is unreliable, which is exactly the
problem Truestock is meant to remove. Removing the buffer without better feeds would increase
cancellations, so it stays until the feeds are live.

## Volumes

| Metric | Value | Period |
| :--- | :--- | :--- |
| Orders per day | 7,400 | Oct 2026 average |
| Average order value | £68.10 | Oct 2026 |
| Conversion rate | 2.9 % | Oct 2026 |
| Split shipments | 38 % of orders | Oct 2026 |
| Stock-related cancellations | 2.4 % of orders | Oct 2026 |

## Related

[Marketplaces](./marketplaces.md) · [Order capture](../order-flow/order-capture.md) ·
[Product page messaging](../../delivery-promise/customer-messaging/product-page-messaging.md)
