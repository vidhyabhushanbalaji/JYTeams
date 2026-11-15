# Escalation

Status: Agreed · Owner: Marcus Feld · Last updated: 2026-11-13

Who to wake up, in what order, and how long they have. Hypercare escalation is stricter than normal
on-call because the platform is new and the customers are watching.

## Tiers

| Tier | Trigger | Responds | Response time |
| :--- | :--- | :--- | :--- |
| 1 | Single alert, self-recovering | On-call engineer | 15 min |
| 2 | Customer-visible issue, one channel | On-call plus hypercare lead | 30 min |
| 3 | Promise wrong for many customers, or data exposure | Hypercare lead, platform lead, programme lead | 15 min |
| 4 | Launch at risk or rollback required | Programme lead and sponsor | 15 min |

## The rota

| Role | Weekday | Weekend |
| :--- | :--- | :--- |
| Primary on-call | Named engineer, 7-day blocks | Same |
| Secondary | Another engineer | Same |
| Hypercare lead | Marcus Feld | Marcus Feld, 08:00–20:00; tier 3+ outside |
| Platform lead | Nadia Kerr | Tier 3+ only |
| Programme lead | Priya Raman | Tier 4 only |

Phone numbers are in the launch rota, not in this document, because a document with phone numbers is a
document that gets copied.

## Who decides what

| Decision | Authority |
| :--- | :--- |
| Restart a service | On-call |
| Apply a warehouse hold | On-call, informing Marcus |
| Soft rollback | Marcus Feld |
| Full rollback | Marcus and Priya jointly |
| Customer communication | Jo Bell, wording approved by Tom Alder |
| Delay the next channel | Marcus with Priya |

## What to include in an escalation

| Field | Example |
| :--- | :--- |
| Impact | "Website quotes are 4× slower, no wrong dates observed" |
| Scope | "All users, website channel only" |
| Since | "09:41" |
| What we tried | "Scaled app instances from 4 to 6, no change" |
| What we need | "Decision on rollback vs fix forward" |

A message without impact and scope gets a question rather than an action, which wastes the first five
minutes of every incident.

## Communication cadence during an incident

| Severity | Updates |
| :--- | :--- |
| Tier 1 | Incident channel only |
| Tier 2 | Every 30 minutes in the channel, plus support briefing |
| Tier 3 | Every 15 minutes, plus a call bridge |
| Tier 4 | Every 15 minutes, plus sponsor update and customer comms draft |

## No-blame, but named

Incident reviews name the system and the decision, not the person. The exception is a deliberate
bypass of a freeze or a rollback veto exercised without writing it down, both of which are handled
through the programme process rather than a shouting match.

## Related

[Hypercare plan](./hypercare-plan.md) · [Rollback triggers](../rollback/rollback-triggers.md) ·
[Runbook index](../runbooks/runbook-index.md)
