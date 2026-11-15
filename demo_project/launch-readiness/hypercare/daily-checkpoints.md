# Daily Checkpoints

Status: Draft · Owner: Marcus Feld · Last updated: 2026-11-13

The twenty-minute meeting that runs every day of hypercare. Its purpose is to stop small problems
becoming a week of incident reviews, and it is short on purpose.

## The five numbers

Read out, not discussed unless red:

| # | Number | Yesterday | Threshold |
| :--- | :--- | :--- | :--- |
| 1 | Promise accuracy, rolling 24 h | — | ≥ 90 % |
| 2 | Orders with a fallback date | — | ≤ 1 % |
| 3 | Oversells | — | 0 |
| 4 | Failed reservations | — | ≤ 0.5 % |
| 5 | Contacts per 100 orders | — | ≤ 5 |

## Standing agenda

| Item | Minutes | Owner |
| :--- | :--- | :--- |
| Numbers | 3 | On-call |
| Customer issues from the last 24 h | 5 | Marcus Feld |
| Feed and carrier status | 3 | Dan Whitcombe |
| Defect delta (new, closed, ageing) | 5 | Aisha Bello |
| Decisions and actions | 4 | Marcus Feld |

## Non-negotiable rules

1. If a number is red, it is the first agenda item and the rest waits.
2. Every action has an owner and a time, not a date.
3. Anything that needs more than five minutes of discussion moves to a separate call.
4. The summary is posted to the programme channel by 09:45, whether or not everyone attended.

## Day summary

The 17:00 summary is four lines:

```text
Accuracy 93.1% (target 90) | Fallback 0.4% | Oversells 0 | Contacts 4.1/100
Closed today: 2 Sev-3 (date copy, locker label)
Open: 1 Sev-2 (store cancel path, fix tonight)
Risk: Northgate feed 18 min stale at 14:20, recovered, monitoring
Tomorrow: marketplaces go live 09:00, war room staffed from 07:00
```

The format is fixed so that it can be read in twenty seconds and compared day to day. A narrative
summary is written only when something happened that the numbers cannot express.

## Weekly review

Every Friday during hypercare, 45 minutes:

| Input | Owner |
| :--- | :--- |
| Seven-day accuracy by service | Aisha Bello |
| Customer verbatims (five) | Marcus Feld |
| Defect trend | Aisha Bello |
| Carrier performance | Gavin Shore |
| Whether the next channel proceeds | Decision |

## Related

[Hypercare plan](./hypercare-plan.md) · [Escalation](./escalation.md) ·
[Promise accuracy](../../delivery-promise/customer-messaging/promise-accuracy.md)
