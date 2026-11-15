# Test Cases — Website Stock Display

Status: Draft · Owner: Aisha Bello · Last updated: 2026-11-13

What the website shows for stock, across the states a customer can encounter. Each case names the
acceptance criterion it proves, because a display test without a criterion becomes a matter of
taste.

## The cases

| ID | Given | When | Then |
| :--- | :--- | :--- | :--- |
| WEB-01 | SKU with 14 units at Midlands, fresh feed | Product page loads | "Order within … for delivery by <date>", date present |
| WEB-02 | SKU with 0 units everywhere | Product page loads | "Out of stock. Notify me." No date |
| WEB-03 | SKU with units only in quarantine | Product page loads | Out of stock (AC-03) |
| WEB-04 | Midlands feed stale by 20 minutes | Product page loads | No date, fallback copy (AC-02) |
| WEB-05 | SKU sold by website and Amazon | Two quotes, 1 second apart | Both quotes show the same availability |
| WEB-06 | Last unit, two browsers | Both quote, then both buy | Exactly one succeeds, one gets a clear message (AC-04) |
| WEB-07 | Order placed 12:31 at Midlands | Confirmation loads | Promise is next working day, not today (AC-10) |
| WEB-08 | Order placed 12:29 at Midlands | Confirmation loads | Promise is today+1 as configured |
| WEB-09 | Bulky item, date 20 days out | Product page loads | "Week commencing …", no day (AC-12) |
| WEB-10 | Variant change (size) | Variant selected | New quote requested, date updates |
| WEB-11 | Basket has bulky and parcel | Basket loads | Two delivery groups, two dates |
| WEB-12 | DPS unavailable | Product page loads | Fallback range, labelled estimate (AC-13) |
| WEB-13 | Pre-order product | Product page loads | Release date, no delivery date |
| WEB-14 | Restricted product (age) | Product page loads | Collection only, no delivery option |
| WEB-15 | Store within 20 miles has stock | Product page loads | Collection line with store name and "today" |

## What each case must also check

| Check | Applies to |
| :--- | :--- |
| Date matches checkout exactly | WEB-01, 07, 09, 11 |
| No countdown outside 6 hours of cut-off | WEB-01 |
| Countdown is static text, not animation | WEB-01 |
| Screen reader announces date once | WEB-01, 09, 12 |
| No stock quantity shown anywhere | All |
| Date is in the customer's locale | All |

## Edge cases worth keeping

**WEB-05** is the case that catches channel drift: two quotes a second apart must agree, and if they
do not, the cache invalidation is wrong rather than the availability. It failed twice in UAT
rehearsals for exactly that reason.

**WEB-06** is the race. It is run with 200 iterations and a fixed random seed so a failure can be
reproduced. A single iteration passes by luck.

**WEB-09** is the bulky horizon. The first implementation showed a day and was caught by legal
review, not by a test, which is why it is now a test.

## Data

| Case | Fixture |
| :--- | :--- |
| WEB-01 | `sku-in-stock-midlands` |
| WEB-02 | `sku-zero-stock` |
| WEB-03 | `sku-quarantine-only` |
| WEB-04 | `feed-stale-midlands` |
| WEB-09 | `sku-bulky-horizon` |
| WEB-15 | `store-near-postcode-bs1` |

Fixtures are in the test environment and are listed in
[test data](../strategy/test-data.md).

## Related

[Acceptance criteria](../strategy/acceptance-criteria.md) · [Product page messaging](../../delivery-promise/customer-messaging/product-page-messaging.md) ·
[Oversell scenarios](./oversell-scenarios.md)
