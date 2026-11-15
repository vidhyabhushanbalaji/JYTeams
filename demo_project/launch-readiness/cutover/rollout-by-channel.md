# Rollout by Channel

Status: Agreed · Owner: Tom Alder · Last updated: 2026-11-06

Why the website goes first, marketplaces second, wholesale third and stores last. The order is not
about size; it is about how quickly we can see a problem and how cheaply we can undo it.

## The order

| Order | Channel | Date | Share | Why here |
| :--- | :--- | :--- | :--- | :--- |
| 1 | Website | 18 May | 52 % | Full control of the interface, one codebase, fastest rollback |
| 2 | Amazon and eBay | 25 May | 34 % | Feed-driven, visible within one push cycle |
| 3 | Wholesale | 1 Jun | 2 % | Low volume, manual desk can absorb problems |
| 4 | Stores and collection | 8 Jun | 8 % | Physical process, needs trained colleagues |

## Why not all at once

A single cutover would test every channel's behaviour simultaneously with no way to tell which one
caused a problem. The staged order gives each channel a week of observation, and each week uses the
same four panels and thresholds.

## Why the website is first

| Property | Value |
| :--- | :--- |
| Interface control | Complete: we ship the frontend |
| Rollback | Feature flag, seconds |
| Observability | Full, including the customer journey |
| Volume | Highest, so problems surface quickly |
| Risk | Contained: no marketplace account health |

Marketplaces first would risk an account warning while we were still learning. Stores first would put
an unfamiliar process in front of colleagues and customers at the same time.

## Channel-specific risks

| Channel | Specific risk | Mitigation |
| :--- | :--- | :--- |
| Website | Traffic shape under real load | 1 % ramp before 100 % |
| Amazon | Account health warning from oversell | Conservative buffer, five-minute push |
| eBay | Defect rate from late dispatch | Dispatch confirmation tested end to end |
| Wholesale | EDI mapping errors | Desk can key orders manually |
| Stores | Colleague unfamiliarity | 40-store pilot, task cards |

## What "live" means per channel

| Channel | Old behaviour at | New behaviour from | Coexistence |
| :--- | :--- | :--- | :--- |
| Website | Stock flag | Promise date | Flag removed, not kept |
| Amazon | 30-min Mercury extract | 5-min ATP push | Old push disabled |
| eBay | 30-min extract | 5-min ATP push | Old push disabled |
| Wholesale | Desk stock check | ATP figure on the desk screen | Desk confirmation stays |
| Stores | Nightly file | Hourly feed + reservation | File stays, cadence changes |

The website's old flag is removed rather than kept as a fallback: two sources of truth is how the
original problem started.

## Criteria between channels

| Check | Threshold |
| :--- | :--- |
| Accuracy over 7 days | ≥ 88 % |
| Oversells | 0 |
| Fallback share | ≤ 1 % |
| Open Sev-1/Sev-2 | 0 |
| Contact volume | ≤ 6 per 100 orders |

If a criterion fails, the next channel waits a week. It does not cancel; waiting is the cheapest
possible response to a bad week.

## Related

[Cutover plan](./cutover-plan.md) · [Timeline](./timeline.md) · [Rollback triggers](../rollback/rollback-triggers.md)
