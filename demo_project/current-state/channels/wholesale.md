# Wholesale Channel

Status: Agreed · Owner: Ruth Iyer · Last updated: 2026-10-28

The wholesale channel serves 2,300 trade accounts through the **Trade at Harbour & Heath** portal
and, for 60 larger accounts, through EDI. It is small in order count and large in value: 240 orders
a day at an average of £640.

## Who buys

| Segment | Accounts | How they order | Typical basket |
| :--- | :--- | :--- | :--- |
| Independent retailers | 1,940 | Trade portal, card or account terms | 8–30 units |
| Garden centres | 210 | Trade portal, account terms | 40–120 units |
| EDI accounts | 60 | EDI 850 purchase order | Pallets, weekly |
| Hospitality | 90 | Trade portal, account terms | 20–60 units |

## How an order is made

Portal orders are created directly in Mercury by the TradePortal service, with `source=wholesale`
and the account's agreed price list. EDI orders land as files in Orbit's inbound directory, are
translated from X12 850, and are acknowledged with an 855 within one business hour. Dispatch
confirmation goes back as an 856 ASN, which several accounts treat as the trigger for their own
goods-in booking.

## Why wholesale is different

Stock is **not reserved** when a wholesale order is placed. A trade order is confirmed by the
wholesale desk after a stock check, usually within four hours, and only then is stock allocated.
This is a commercial choice: wholesale customers accept a partial fulfilment and a backorder,
whereas a consumer expects the exact item.

That difference is the single biggest complication in the reservation policy, because the same SKU
can be promised to a consumer while a trade order is waiting for a human to confirm it.

## The EDI quirks

| Quirk | Detail | Handling |
| :--- | :--- | :--- |
| Order changes after submission | 850 amendments are not supported by 22 accounts | Desk emails a corrected order; manual entry |
| Unit of measure | Some accounts order in cases, others in singles | Atlas holds a case pack size per SKU |
| Delivery windows | 14 accounts require a booking slot | Mercury free-text field, read by the desk |
| Price list version | Customers on 2024 prices still exist | Three price lists active until 2027-03-31 |

## Volumes

| Metric | Value |
| :--- | :--- |
| Orders per day | 240 |
| Lines per order | 11 on average |
| Partial fulfilments | 12 % of orders |
| Backorders | 6 % of lines |
| Days to dispatch (median) | 2.4 |

## What changes under Truestock

Wholesale stays on the portal and EDI, but availability becomes shared: the wholesale desk will see
the same ATP figure the website shows, and confirmed trade orders will create a hard allocation.
Nothing about the confirmation step changes before launch; that is a post-peak discussion.

## Related

[Stores](./stores.md) · [Reservation rules](../../reservation-policy/policy/reservation-rules.md) ·
[Integration landscape](../systems/integration-landscape.md)
