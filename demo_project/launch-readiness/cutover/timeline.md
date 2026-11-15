# Cutover Timeline

Status: Draft · Owner: Marcus Feld · Last updated: 2026-11-13

Every launch event from the first rehearsal to hypercare exit, in one table. Dates are fixed and
anything that moves is a change request.

## Full timeline

| Date | Event | Owner | Duration |
| :--- | :--- | :--- | :--- |
| 2027-02-26 | Mercury hotfix to production | Dan Whitcombe | 2 h |
| 2027-03-01 | UAT environment built | Nadia Kerr | 3 days |
| 2027-03-05 | DPIA signed; beta recruitment opens | Leah Okafor | — |
| 2027-03-08 | Penetration test begins | Nadia Kerr | 5 days |
| 2027-03-11 | Cutover rehearsal 1 | Marcus Feld | 4 h |
| 2027-03-26 | UAT environment refresh | Nadia Kerr | 1 day |
| 2027-04-06 | UAT starts | Aisha Bello | 25 days |
| 2027-04-12 | Beta wave 1 (100 customers) | Tom Alder | 4 days |
| 2027-04-16 | Beta wave 2 (400 customers) | Tom Alder | 10 days |
| 2027-04-22 | Cutover rehearsal 2 | Marcus Feld | 4 h |
| 2027-04-26 | Beta closes; week 2 report issued | Aisha Bello | — |
| 2027-04-30 | UAT exit and sign-off | Aisha Bello | 90 min |
| 2027-05-04 | Go/no-go paper circulated | Priya Raman | — |
| 2027-05-11 | Go/no-go decision | Steering group | 90 min |
| 2027-05-13 | Final launch rehearsal, production config | Nadia Kerr | 3 h |
| 2027-05-17 | Comms to stores, carriers, contact centre | Jo Bell | — |
| 2027-05-18 | Website live | Marcus Feld | 1 day |
| 2027-05-25 | Marketplaces live | Tom Alder | 1 day |
| 2027-06-01 | Wholesale live | Ruth Iyer | 1 day |
| 2027-06-08 | Store collection live | Elena Vasquez | 1 day |
| 2027-06-15 | Hypercare exit | Marcus Feld | — |
| 2027-10-25 | Peak change freeze | Priya Raman | — |

## Launch days in detail

| Day | Channel | Traffic share | Rollback window |
| :--- | :--- | :--- | :--- |
| 18 May | Website | 52 % | 45 min |
| 25 May | Amazon and eBay | 34 % | 45 min per marketplace |
| 1 Jun | Wholesale | 2 % | 2 hours |
| 8 Jun | Stores and collection | 8 % | 45 min |

Wholesale gets a longer rollback window because there are only 240 orders a day and the desk can
revert manually, which makes a slow rollback acceptable.

## What happens between launches

Each week has a daily 09:15 check with the same four panels as the war room, and a Friday review that
decides whether the next channel proceeds. The default is to proceed; stopping requires a named reason,
so drift is harder than a decision.

| Check | Threshold to proceed |
| :--- | :--- |
| Promise accuracy | ≥ 88 % over 7 days |
| Oversells | 0 in the channel already launched |
| Fallback share | ≤ 1 % |
| Contacts per 100 orders | ≤ 6 |
| Open Sev-1/Sev-2 | 0 |

## Slack

| Gap | Days | Use |
| :--- | :--- | :--- |
| UAT exit to go/no-go | 4 | Paper, not work |
| Go/no-go to website | 7 | Rehearsal, comms |
| Website to marketplaces | 7 | Stabilise |
| Marketplaces to wholesale | 7 | Stabilise |
| Stores to hypercare exit | 7 | Close out |

There is no slack between UAT exit and go/no-go, which is intentional: if UAT needs an extension, the
go/no-go moves, and that is a steering decision rather than a quiet reshuffle.

## Related

[Cutover plan](./cutover-plan.md) · [Rollout by channel](./rollout-by-channel.md) ·
[Hypercare plan](../hypercare/hypercare-plan.md)
