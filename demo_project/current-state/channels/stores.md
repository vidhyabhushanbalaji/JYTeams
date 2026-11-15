# Store Channel

Status: Agreed · Owner: Elena Vasquez · Last updated: 2026-10-28

184 stores sell through `StorePOS` and act as collection points for online orders. Stores hold
about 22 % of our stock by value, but the stock file they send us is a nightly batch that is 91 %
accurate, which makes click and collect the least reliable promise we make.

## The numbers

| Metric | Value | Source |
| :--- | :--- | :--- |
| Stores | 184 | Estate list, Oct 2026 |
| Click and collect orders per day | 1,100 | Mercury, Oct 2026 |
| Collected within 48 hours | 82 % | StorePOS |
| Stock accuracy | 91 % | 1,240 self-audits, Sep 2026 |
| Store stock file cadence | Nightly, 23:30 | StoreStock |
| Stores with handheld scanners | 96 of 184 | Estate audit |

## How store stock reaches us

`StoreStock` runs on the in-store back office and exports a full file at 23:30. The file is
transferred by Orbit to Mercury, which applies it as the store's available quantity. There is no
delta feed: the whole estate is sent every night, about 41 MB, and applied in a 40-minute batch.

Consequences:

1. A sale at 10:00 is invisible to the website until the next morning.
2. A stock correction made during a delivery is invisible until the next morning.
3. Returns processed in store are reflected the same night, at best.

## Why accuracy is 91 %

The 1,240 audits found three recurring causes:

| Cause | Share of errors |
| :--- | :--- |
| Deliveries booked in at case level, sold as singles | 41 % |
| Theft and damage not written off | 28 % |
| Transfers between stores recorded only at the sending store | 22 % |
| Returns put back on the shelf without a system entry | 9 % |

The 88 stores without handheld scanners account for most of the first two causes, which is why the
store estate programme is buying 2,400 devices during 2027.

## What collection promises today

The website offers collection when the store file says the item is there. **18 % of collection
orders** are cancelled because the store cannot find the item on the shelf, and the customer finds
out by email up to four hours later. Stores with scanners cancel at 9 %; stores without, at 24 %.

## What changes under Truestock

Store stock moves to an hourly batch from February 2027 (CR-007), still a full file but more often,
and collection promises start using a 30-minute soft reservation at the chosen store. The
reservation buys the store time to pick before another channel can sell the item. Accuracy remains
the constraint: the promise target for collection is deliberately lower than for delivery until
the device rollout finishes.

## Related

[Store collection reservation](../../reservation-policy/edge-cases/store-collection.md) ·
[Store stock network](../../stock-feeds/warehouses/store-stock-network.md) ·
[Store collection test scenarios](../../customer-testing/test-cases/store-collection-scenarios.md)
