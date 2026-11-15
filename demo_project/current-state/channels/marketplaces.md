# Marketplace Channels

Status: Agreed · Owner: Ruth Iyer · Last updated: 2026-10-28

Amazon UK and eBay UK together are 34 % of order volume. Both are run through **ChannelBridge**, a
third-party integrator that pushes our stock out and pulls orders in. Neither marketplace tolerates
an oversell for long: Amazon suspends listings after repeated inventory failures, and eBay applies
defect-rate penalties.

## The numbers

| Metric | Amazon UK | eBay UK |
| :--- | :--- | :--- |
| Orders per day | 3,700 | 1,150 |
| Average order value | £54 | £41 |
| Live listings | 28,400 | 41,200 |
| Inventory push cadence | 30 minutes | 30 minutes |
| Order pull cadence | 5 minutes | 5 minutes |
| Oversell rate | 1.8 % | 2.9 % |
| Account health | Good, two warnings in 2026 | Above standard, no defects |

## How stock gets to a marketplace

ChannelBridge takes a Mercury extract every 30 minutes, translates it into Amazon's inventory
feed and eBay's quantity update, and posts it. The extract itself is generated up to 40 minutes
before that, so the true age of a marketplace quantity is between 30 and 70 minutes. During
promotions it is worse, because Mercury's extract queue backs up.

Each marketplace has its own stock pool: Amazon draws from Midlands DC and Northgate Fulfilment,
eBay from all four warehouses. Neither pool is reserved against the other, which is where the
largest oversell losses occur.

## How orders arrive

ChannelBridge creates an order in Mercury through the same Orbit endpoint the website uses, with
`source=amazon` or `source=ebay`, plus the marketplace order ID. Two quirks matter:

- Amazon sends a **pending** order before it is confirmed. Mercury used to route pending orders and
  had to be changed in 2024; the flag is now respected but it is easy to regress.
- eBay allows a buyer to request a cancellation up to an hour after purchase; roughly 90 of those
  arrive per day and 40 % are rejected because the order already shipped.

## What we owe marketplace partners

| Obligation | Amazon | eBay |
| :--- | :--- | :--- |
| Dispatch confirmation | Within 1 business day | Within 2 business days |
| Tracking upload | Required, same day | Required, same day |
| Cancellation reason codes | Mandatory | Not required |
| Late dispatch tolerance | 4 % | 5 % |

## The painful part

Marketplace stock is a single number per SKU, and we cannot tell Amazon "9 in Midlands but 2 of
them are already picked". Under Truestock, the availability service computes the marketplace figure
from reserved and unreserved stock, and the push cadence shortens to five minutes. That change is
in [ADR 0004](../../decisions/0004-poll-marketplace-inventory.md).

## Related

[Website](./website.md) · [Wholesale](./wholesale.md) ·
[Marketplace stock display testing](../../customer-testing/test-cases/marketplace-stock-display.md)
