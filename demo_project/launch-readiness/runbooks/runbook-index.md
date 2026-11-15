# Runbook Index

Status: Draft · Owner: Marcus Feld · Last updated: 2026-11-13

Five runbooks for the things most likely to go wrong at an inconvenient hour. Each is written to be
followed by someone who did not build the system, under time pressure, without asking anyone.

## The runbooks

| Runbook | Use when | First action | Owner |
| :--- | :--- | :--- | :--- |
| [Stock feed failure](./stock-feed-failure.md) | A warehouse feed stops or sends bad data | Check whether the source is stale or wrong | Dan Whitcombe |
| [ATP service outage](./atp-service-outage.md) | Availability lookups fail or are very slow | Confirm scope, then decide fallback or rollback | Nadia Kerr |
| [Carrier API failure](./carrier-api-failure.md) | Serviceability or booking calls fail | Serve cached serviceability, queue bookings | Gavin Shore |
| [Oversell surge](./oversell-surge.md) | More than five oversells in an hour | Hold the suspect warehouse | Marcus Feld |
| [Rollback](../rollback/rollback-plan.md) | A hard trigger fires | Follow the rollback sequence | Marcus Feld |

## How a runbook is written

| Rule | Why |
| :--- | :--- |
| First line states the symptom, not the cause | The reader knows only what they see |
| Every step is an action, not a question | Decisions belong in a separate box |
| Commands are copy-pasteable | Typing at 02:00 produces typos |
| Each step says how to verify it worked | Otherwise nobody knows when to stop |
| Escalation is on page one | The reader may need it in five minutes |
| Customer impact is stated in the first screen | It changes every later decision |

## What is deliberately not a runbook

| Not a runbook | Where it lives |
| :--- | :--- |
| How to deploy a release | Release process |
| How to add a carrier | Carrier onboarding |
| How to change a policy rule | Policy configuration |
| How to reconcile stock | Reconciliation report |
| How to train an agent | Contact centre briefing |

A runbook is for an unplanned event with a time limit. Everything else is a process.

## Testing the runbooks

| Activity | When | Who |
| :--- | :--- | :--- |
| Tabletop walkthrough | 2027-04-15 | Marcus, Nadia, Dan |
| Live drill: feed failure | 2027-04-22 | On-call engineer |
| Live drill: ATP outage | 2027-04-29 | On-call engineer |
| Review after any use | Within 5 days | Owner |

The tabletop has one rule: the person following the runbook has not read it before. That is the only
way to find the step that assumes knowledge.

## Related

[Hypercare plan](../hypercare/hypercare-plan.md) · [Rollback triggers](../rollback/rollback-triggers.md) ·
[Stale stock handling](../../stock-feeds/reliability/stale-stock-handling.md)
