# UAT Plan

Status: Draft · Owner: Aisha Bello · Last updated: 2026-11-13

User acceptance testing runs 6–30 April 2027 with business teams, on UAT data, against the policy as
written. Its job is to answer one question: does the platform do what the business agreed, including
the awkward parts.

## Who tests what

| Team | Lead | Scenarios | Days |
| :--- | :--- | :--- | :--- |
| Fulfilment | Sofia Mendes | Reservation rules, quarantine, allocation | 6 |
| Trading | Ruth Iyer | Channel display, marketplace, pricing display | 4 |
| Store operations | Elena Vasquez | Collection, pick tasks, store stock | 4 |
| Customer operations | Marcus Feld | Contact centre screens, fallbacks, holds | 3 |
| Finance | Ben Osei | Reconciliation, ledger gap, month-end impact | 2 |
| Data protection | Leah Okafor | Postcode logging, retention, beta consent | 1 |

Each team has a named tester and a named deputy. A team that cannot field both on a given day does not
get a slot, because a single tester on holiday is how a fortnight of UAT becomes four days.

## Structure of the window

| Week | Focus | Exit check |
| :--- | :--- | :--- |
| 1 (6–9 Apr) | Core reservation and promise journeys | No Sev-1; all P1 scenarios executed |
| 2 (12–16 Apr) | Channels, stores, edge cases | 90 % of scenarios executed |
| 3 (19–23 Apr) | Regression after fixes, failure scenarios | No open Sev-1 or Sev-2 |
| 4 (26–30 Apr) | Sign-off, evidence review | Signed record |

Beta runs in weeks 2 and 3 alongside, which is intentional and is the largest scheduling risk in the
plan. Aisha and Tom share a daily 15-minute triage during that overlap.

## Scenario priority

| Priority | Meaning | Count |
| :--- | :--- | :--- |
| P1 | Must pass before go/no-go | 21 |
| P2 | Must pass before hypercare exit | 12 |
| P3 | Nice to verify, can slip | 5 |

Thirty-eight scenarios, almost all traceable to an acceptance criterion. The five P3 scenarios are
documented in the tracker and are the first thing to drop if time runs short.

## How testing is run

| Element | Detail |
| :--- | :--- |
| Environment | UAT, refreshed 2027-04-04 |
| Data | Masked October orders plus fixtures |
| Entry | Through the real interfaces, no API shortcuts |
| Evidence | Screenshot or log per scenario, attached to the record |
| Defects | Raised in the tracker with severity, no verbal reports |

The "no verbal reports" rule exists because three defects in the October rehearsal were discussed in
stand-up and never written down, and two of them were then rediscovered in week 3.

## Daily rhythm

| Time | What | Who |
| :--- | :--- | :--- |
| 09:15 | Triage: new defects, blockers | Aisha, workstream leads |
| 13:00 | Midday check on scenario progress | Aisha |
| 16:30 | Status note to the programme channel | Aisha |

The 16:30 note is three lines: scenarios executed, defects open by severity, anything blocked. It
replaces a meeting.

## Related

[Exit criteria](./entry-and-exit-criteria.md) · [Defect triage](./defect-triage.md) ·
[Test cases](../test-cases/)
