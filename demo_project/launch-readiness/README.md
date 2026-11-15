# Launch Readiness

Status: In review · Owner: Marcus Feld · Last updated: 2026-11-13

The workstream that turns a working platform into a launch: cutover, rollback, hypercare, comms and
the runbooks someone reads at 02:00. It starts in earnest in February 2027 but its decisions are being
made now, because a rollback plan written in May is a plan written too late.

## The launch in one line

Website on 18 May 2027, marketplaces a week later, wholesale the week after, store collection on 8
June, hypercare for four weeks, all before the peak freeze on 25 October.

## What lives here

| Question | Document |
| :--- | :--- |
| How do we switch over? | [Cutover plan](./cutover/cutover-plan.md) |
| What is the order of events? | [Timeline](./cutover/timeline.md) |
| What must be true to go? | [Go/no-go checklist](./cutover/go-no-go-checklist.md) |
| Which channel goes first, and why? | [Rollout by channel](./cutover/rollout-by-channel.md) |
| What if it goes wrong? | [Rollback plan](./rollback/rollback-plan.md) · [Triggers](./rollback/rollback-triggers.md) |
| Who is watching, and when? | [Hypercare plan](./hypercare/hypercare-plan.md) |
| Who tells whom? | [Comms](./comms/internal-comms.md) |
| What does on-call do at 02:00? | [Runbooks](./runbooks/runbook-index.md) |

## The four launch risks

| Risk | Why it matters | Where it is handled |
| :--- | :--- | :--- |
| A feed goes stale during cutover | The first thing a customer sees is a wrong date | Pre-cutover feed check, hold switch |
| A channel behaves differently under real traffic | Marketplace and store traffic is unlike website traffic | Staged rollout by channel |
| Support cannot answer promise questions | Volume rises even when accuracy is good | Briefing, scripts, hypercare rota |
| Rollback is slower than the incident | Damage compounds while we decide | Rehearsed twice, 45-minute target |

## Dates

| Milestone | Date |
| :--- | :--- |
| Cutover rehearsal 1 | 2027-03-11 |
| Cutover rehearsal 2 | 2027-04-22 |
| Go/no-go | 2027-05-11 |
| Website live | 2027-05-18 |
| Marketplaces live | 2027-05-25 |
| Wholesale live | 2027-06-01 |
| Stores and collection live | 2027-06-08 |
| Hypercare exit | 2027-06-15 |
| Peak freeze | 2027-10-25 |

## What "ready" means

Ready is not "the tests passed". Ready means: the checklist is complete, the rollback has been
rehearsed under time pressure, the contact centre can answer the five most likely questions, and a
named person is awake and empowered to stop the launch. Any one of those missing and the launch
waits.

## Related

[Project overview](../README.md) · [Milestones](../programme/plan/milestones.md) ·
[UAT sign-off](../customer-testing/uat/sign-off.md)
