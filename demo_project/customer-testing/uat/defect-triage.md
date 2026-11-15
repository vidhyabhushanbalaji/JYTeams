# Defect Triage

Status: Agreed · Owner: Aisha Bello · Last updated: 2026-11-06

Severity definitions, the triage rhythm and the rules that stop a defect list from becoming a
negotiation. The most important rule is first: **a wrong customer promise is Sev-1**, however small
the code change that caused it.

## Severity

| Severity | Definition | Examples | Response |
| :--- | :--- | :--- | :--- |
| Sev-1 | A customer can be given a wrong promise or sold stock that does not exist | Oversell, date wrong by more than a day, reservation lost | Fix immediately, block exit |
| Sev-2 | A core journey is broken or a rule is not enforced, with no wrong promise | Release without reason code, fallback not shown, split not predicted | Fix before exit |
| Sev-3 | A secondary journey is affected or a display is wrong | Copy mismatch, confidence caveat missing, sorting wrong | Fix before hypercare exit |
| Sev-4 | Cosmetic or internal only | Log wording, admin label | Backlog |

Severity is about the customer consequence, not the technical cause. A one-line bug that produces
tomorrow's date for a Wednesday delivery is Sev-1, and it stays Sev-1 even if it is fixed in ten
minutes.

## Priority versus severity

| | High priority | Low priority |
| :--- | :--- | :--- |
| **Sev-1** | Always first | Not a thing: Sev-1 is always first |
| **Sev-2** | Fix in this window | Fix before exit |
| **Sev-3** | Fix if capacity | Defer with a date |
| **Sev-4** | Only if trivial | Backlog |

Priority can move a fix order; it can never move a severity.

## Triage rhythm

| When | Who | Purpose |
| :--- | :--- | :--- |
| Daily 09:15 | Aisha, workstream lead, engineer | Assign, confirm severity |
| On a Sev-1, immediately | Aisha, Nadia, owner | Stop, fix, verify |
| Friday | Programme board | Sev-3 ageing and deferrals |

A Sev-1 bypasses triage: whoever finds it calls the on-call engineer and Aisha, and the tracker entry
follows within the hour.

## What a defect record must contain

| Field | Why |
| :--- | :--- |
| Scenario ID and acceptance criterion | Traceability |
| Expected versus actual | Removes ambiguity |
| Evidence (screenshot, log, trace ID) | Prevents "cannot reproduce" loops |
| Environment and data | Reproducibility |
| First seen | Ageing |
| Severity and rationale | Consistency |

## Common disputes

| Dispute | Resolution |
| :--- | :--- |
| "It is only a copy change" | If the copy changes the promise, it is Sev-1 |
| "It happens rarely" | Frequency affects priority, not severity; record both |
| "It is a data problem, not a code problem" | Still a defect; the record names the data owner |
| "It only affects test data" | Unless the data is unrealistic, it counts |
| "It is working as designed" | Then the design is wrong and needs a change request |

The last row has happened twice in the programme, and both times the design was changed.

## Current position

| Severity | Open | Oldest |
| :--- | :--- | :--- |
| Sev-1 | 0 | — |
| Sev-2 | 3 | 2026-11-06 (store cancel path) |
| Sev-3 | 11 | 2026-10-30 |
| Sev-4 | 24 | 2026-10-09 |

The Sev-2 count is expected to grow once UAT starts; three is low because UAT has not run. The Sev-4
backlog is deliberately not groomed before launch.

## Related

[UAT plan](./uat-plan.md) · [Exit criteria](./entry-and-exit-criteria.md) ·
[Test strategy](../strategy/test-strategy.md)
