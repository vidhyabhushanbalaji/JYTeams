# Rollback Triggers

Status: Agreed · Owner: Marcus Feld · Last updated: 2026-11-13

The numbers and events that mean "stop". They are agreed in advance, written down, and owned by one
person so that a decision at 03:00 does not require a committee.

## Who decides

| Situation | Decides | Consulted |
| :--- | :--- | :--- |
| Soft rollback during launch | Marcus Feld | Priya Raman, Nadia Kerr |
| Full rollback | Marcus Feld and Priya Raman jointly | Nadia Kerr, Sofia Mendes |
| Rollback outside launch hours | On-call engineer | Launch lead by phone |
| Warehouse hold | Marcus Feld | Dan Whitcombe |

Marcus is the decision-maker because the customer relationship is his to protect. Nadia can veto a
rollback that would itself cause harm, and that veto has to be exercised in writing in the incident
channel.

## Hard triggers (roll back, do not discuss)

| Trigger | Threshold | Why |
| :--- | :--- | :--- |
| Oversells in one hour | ≥ 10 | The core failure the platform prevents |
| Promise accuracy in the last hour | < 60 % | Worse than the system being replaced |
| Reservations failing | > 20 % of attempts | Customers cannot buy |
| Availability errors | > 5 % of requests | The site is effectively broken |
| Wrong warehouse data accepted | Confirmed | Means bad stock, not bad luck |
| Data exposure | Any | Security incident |

## Soft triggers (roll back unless there is a specific reason not to)

| Trigger | Threshold |
| :--- | :--- |
| Fallback share | > 15 % for 30 minutes |
| Product page latency p95 | > 2 s |
| Feed excluded | Both own DCs at once |
| Contact volume | > 3× baseline for 60 minutes |
| Duplicate reservations | Any confirmed |

## What is not a trigger

| Not a trigger | Why |
| :--- | :--- |
| A single wrong date | Investigate, fix, do not roll back |
| One carrier API down | Fallback handles it |
| A marketplace push delayed | Five-minute cadence absorbs it |
| A support queue of promise questions | Expected in week one |
| A Sev-2 defect | Fix forward, unless it produces wrong promises |

The fourth row is important: call volume rises after any change, and rolling back every time the phone
rings would make the platform impossible to launch.

## Escalation when a trigger fires

| Time | Action |
| :--- | :--- |
| 0 min | On-call acknowledges, opens the incident channel |
| 5 min | Launch lead and platform lead joined |
| 10 min | Trigger confirmed or dismissed with evidence |
| 15 min | Rollback decision recorded |
| 20 min | Comms to support and, if needed, the sponsor |
| 45 min | Rollback complete or escalated to full |

The 10-minute confirmation step exists because two of the soft triggers can fire from a single feed
hiccup, and a rollback is itself disruptive.

## After a false alarm

| Action | Owner |
| :--- | :--- |
| Record the trigger, the evidence and why it was dismissed | On-call |
| Adjust the threshold if it fired spuriously | Nadia Kerr |
| Tell the support team, so they can answer questions | Marcus Feld |

Thresholds that fire falsely get adjusted once. A threshold that fires falsely twice is removed and
replaced with a different signal.

## Related

[Rollback plan](./rollback-plan.md) · [Hypercare escalation](../hypercare/escalation.md) ·
[Runbook index](../runbooks/runbook-index.md)
