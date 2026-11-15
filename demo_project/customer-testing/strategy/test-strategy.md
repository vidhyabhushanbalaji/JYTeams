# Test Strategy

Status: Agreed · Owner: Aisha Bello · Last updated: 2026-11-13

Six levels of testing, each with a job the others cannot do, and a deliberate rule that the same
person does not sign off a level they built.

## Levels

| Level | Scope | Owner | Cadence | Pass means |
| :--- | :--- | :--- | :--- | :--- |
| Unit | Functions, scoring, date arithmetic | Engineers | Every commit | No regressions |
| Integration | Feeds, carriers, Mercury, Horizon | Dan Whitcombe | Nightly | Contracts hold |
| System | End-to-end journeys, all rules | Aisha Bello | Weekly from March | Journeys behave |
| UAT | Business scenarios, policy rules | Business leads | 6–30 April | Business accepts |
| Beta | Real customers, real orders | Tom Alder | 12–26 April | Accuracy and feedback |
| Operational | Peak load, failure, rollback | Nadia Kerr | March–May | SLOs and recovery |

## What each level deliberately does not do

| Level | Not responsible for |
| :--- | :--- |
| Unit | Anything involving a real carrier or a real feed |
| Integration | Customer experience or copy |
| System | Business priorities or acceptance |
| UAT | Technical root-cause analysis |
| Beta | Volume beyond 400 customers |
| Operational | Functional correctness |

The separation matters because the programme has two engineers and a QA lead, not a test department.
Every level that tries to cover everything becomes a slow, unreliable suite that people skip.

## Test pyramid, in numbers

| Level | Count | Runtime | Runs |
| :--- | :--- | :--- | :--- |
| Unit | 940 | 90 s | Every commit |
| Integration | 180 | 14 min | Nightly |
| System | 64 journeys | 40 min | Nightly from March |
| UAT scripts | 38 | 3 days | Fixed window |
| Beta | 400 customers | 2 weeks | Once |
| Operational scenarios | 12 | 6 hours | Three rehearsals |

The unit count is not a target. It is what exists because scoring, date arithmetic and the
availability formula each have many edge cases that are cheaper to test than to reason about.

## Entry and exit

| Level | Entry | Exit |
| :--- | :--- | :--- |
| Integration | Contracts signed for at least three sources | All five sources pass a full replay |
| System | Feeds and carriers stable in UAT | All 64 journeys pass, no Sev-1/2 |
| UAT | System exit met, policy rules frozen | Business sign-off per scenario |
| Beta | DPIA signed, cohort consented, support briefed | Accuracy ≥ 88 % and no Sev-1 |
| Operational | UAT exit met | Load, failure and rollback rehearsals pass |

## Defect handling

Severity is defined once, in [defect triage](../uat/defect-triage.md), and used everywhere. The rule
that matters: **a defect that produces a wrong customer promise is Sev-1**, whatever its technical
size, because the promise is the product.

## What we test that is unusual

| Area | Why it is in scope |
| :--- | :--- |
| Feed staleness | The main real-world failure mode |
| Reservation races | Concurrency on a hot SKU |
| Partial and split orders | 38 % of real orders |
| Postcode edge cases | 1.9 % of postcodes cannot take bulky |
| Copy consistency | Four promises for one order was the original problem |
| Rollback | A launch without a tested rollback is not a launch |

## Not in scope

Wholesale backorder allocation, the Horizon ledger, store stock accuracy itself, and marketplace
listing management. All four are real, none changes between now and launch, and including them would
make UAT a programme of its own.

## Related

[Acceptance criteria](./acceptance-criteria.md) · [Environments](./environments.md) ·
[Test data](./test-data.md)
