# Current State

Status: Agreed · Owner: Dan Whitcombe · Last updated: 2026-11-06

How an order reaches a warehouse today, for each of our five sales channels, and where that path
fails. This workstream is finished: everything here was accepted by Sofia Mendes on 2026-11-06 and
is the baseline every later design is measured against.

## The short version

Harbour & Heath takes **14,200 orders a day** across five channels, and every one of them ends up
as a file, message or manual instruction to one of four warehouses or a store. Stock is not held centrally:
each warehouse and each marketplace keeps its own count, and Mercury reconciles them in a nightly
run. The result is an **oversell rate of 2.1 %**, a **stock display that can be 14 hours old**, and
**38 % of orders shipped in more than one parcel**.

## Read it in this order

| If you want to know | Start here |
| :--- | :--- |
| Where orders come from, and their volumes | [Channels](./channels/) then [Order volume baseline](./channels/order-volume-baseline.md) |
| What happens after "place order" | [Order capture](./order-flow/order-capture.md) and [Routing rules](./order-flow/routing-rules.md) |
| Why stock is wrong | [Known failures](./order-flow/known-failures.md) |
| Which systems are involved | [Integration landscape](./systems/integration-landscape.md) |
| What people told us | [Discovery findings](./interviews/discovery-findings.md) |

## Five facts worth remembering

1. Mercury routes an order to a warehouse using a rules table last changed in 2023, and it does not
   know what stock is actually in the building.
2. Amazon and eBay stock is pushed by ChannelBridge every 30 minutes from a Mercury extract that is
   itself up to 40 minutes old.
3. Store stock is a nightly file. Stores are 91 % accurate, measured by 1,240 self-audits in
   September.
4. Riverside Logistics handles bulky goods on a 15-minute delta feed that we receive but do not
   apply to the website.
5. 31 % of contact-centre calls in September were "where is my order" or "your website said it was
   in stock".

## What this workstream does not decide

Nothing here recommends a fix. Recommendations live in
[reservation-policy](../reservation-policy/README.md) and [stock-feeds](../stock-feeds/README.md); this
folder only records what is true today, with the evidence behind it.

## Related

[Project overview](../README.md) · [Discovery findings](./interviews/discovery-findings.md) ·
[Reservation policy](../reservation-policy/README.md)
