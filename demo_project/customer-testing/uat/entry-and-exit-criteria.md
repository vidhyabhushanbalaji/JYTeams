# Entry and Exit Criteria

Status: Draft · Owner: Aisha Bello · Last updated: 2026-11-13

What must be true before UAT starts, and what must be true before it can sign off. Both lists are
deliberately short and measurable, because a long list of criteria is a list nobody checks.

## Entry criteria (must all be true on 6 April 2027)

| ID | Criterion | Owner | Evidence |
| :--- | :--- | :--- | :--- |
| EN-01 | Reservation policy v1.0 signed, no open rules | Sofia Mendes | Rule table |
| EN-02 | All five feeds replayed successfully in UAT | Dan Whitcombe | Integration report |
| EN-03 | Carrier sandboxes live and verified | Gavin Shore | Onboarding checklist |
| EN-04 | UAT environment built, refreshed, access granted | Nadia Kerr | Environment record |
| EN-05 | System testing complete, no Sev-1 or Sev-2 | Aisha Bello | System test report |
| EN-06 | Test data loaded and masked | Aisha Bello | Data record |
| EN-07 | Defect process and tracker open | Aisha Bello | Tracker |
| EN-08 | Business testers named, booked and briefed | Priya Raman | UAT plan |

EN-01 is the one that is genuinely at risk: RSV-06 is not decided until 2026-12-03, and a policy
change after 2027-01-11 needs a change request. If it slips, UAT starts against a draft policy, which
is worse than starting a week later.

## Exit criteria (must all be true by 30 April 2027)

| ID | Criterion | Threshold |
| :--- | :--- | :--- |
| EX-01 | All P1 scenarios executed | 21 of 21 |
| EX-02 | P1 scenarios passed | 21 of 21 |
| EX-03 | P2 scenarios passed | ≥ 11 of 12 |
| EX-04 | Sev-1 defects open | 0 |
| EX-05 | Sev-2 defects open | 0 |
| EX-06 | Sev-3 defects open | ≤ 15, each with an owner and a date |
| EX-07 | Acceptance criteria measured | 18 of 18 measurable |
| EX-08 | Beta verdict received | Report issued |
| EX-09 | Reconciliation run for 10 consecutive days in tolerance | 10 of 10 |
| EX-10 | Business sign-off recorded per team | 6 of 6 |

EX-09 is easy to overlook and important: a platform that passes every functional test but cannot
reconcile its stock with Horizon is not ready, because finance cannot close the month.

## What happens when a criterion fails

| Failure | Response |
| :--- | :--- |
| Sev-1 open at exit | No sign-off; escalate to steering the same day |
| Sev-2 open at exit | No sign-off; fix and re-test in a 3-day extension |
| P2 scenario failed | Sign-off with a recorded exception and a fix date before hypercare exit |
| Reconciliation out of tolerance | Investigate; if unresolved, sign-off is conditional on a daily manual check |
| Beta verdict negative | No sign-off; the go/no-go paper cannot proceed |

The distinction between "no sign-off" and "conditional sign-off" is deliberate. A Sev-2 leaving a
promise wrong is not a condition; a P2 screen that shows the wrong reason code is.

## Extension

The window can extend by up to three working days without a change request, provided the extension is
recorded and the go/no-go date holds. Beyond that, M6 moves, which is a steering decision.

## Related

[UAT plan](./uat-plan.md) · [Sign-off](./sign-off.md) · [Acceptance criteria](../strategy/acceptance-criteria.md)
