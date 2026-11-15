# Interview — Channel Operations

Status: Agreed · Owner: Priya Raman · Last updated: 2026-10-21

Interview with **Ruth Iyer** (Head of Trading) and **Kelvin Adu** (Marketplace Manager) on
2026-10-14, 60 minutes, at head office. Notes are lightly edited; quotes are exact.

## What they told us

> "The stock number on Amazon is a guess we make every half hour. When it is wrong, Amazon does not
> care why." — Kelvin

> "We turn stock off before a promotion rather than trust the feed. That is revenue we are choosing
> not to take." — Ruth

The trading team manages promotion risk by manually suppressing stock in ChannelBridge before every
campaign: 14 times between September and October 2026. Each suppression costs an estimated £4,000
in lost sales and takes about 40 minutes of Kelvin's time.

## The three things that annoy them most

| Rank | Problem | Detail |
| :--- | :--- | :--- |
| 1 | Promotional stock suppression | Manual, blunt, and used as a substitute for accurate stock |
| 2 | Marketplace oversell warnings | Two Amazon warnings in 2026, one within four units of suspension |
| 3 | No visibility of allocation | Trading cannot see how stock is split between channels |

## On a single stock pool

Ruth is explicit that a single pool is a trading decision, not a technical one: "If I have 40 units
and three channels, I want to decide who gets them, and I want that decision to be honest." She
wants channel-level allocation rules eventually, but accepts that the first release shows one
shared number and relies on the reservation to prevent double-selling.

## What they need from the new system

- A stock figure per SKU per channel that is no more than five minutes old at peak.
- An alert when a marketplace inventory push fails, rather than discovering it from an account
  warning.
- The ability to cap a channel's share of stock during a promotion without switching the channel
  off.

The third is out of scope for this release and recorded as a post-peak candidate. The first two are
in the delivery scope.

## Concerns

Kelvin is worried the five-minute push will increase API errors, because ChannelBridge already
throttles at 220 calls a minute during promotions. That concern is reflected in DEP-06 and in
[marketplaces](../channels/marketplaces.md): the quota increase is a prerequisite, not a nice-to-have.

## Related

[Discovery findings](./discovery-findings.md) · [Marketplace channel](../channels/marketplaces.md) ·
[DEP-06](../../programme/plan/dependencies.md)
