# Dependencies

Status: In review · Owner: Priya Raman · Last updated: 2026-11-13

Cross-workstream dependencies, with the date the receiving workstream needs them. A dependency is
only closed when the receiver confirms it, not when the supplier says it is done.

| ID | From | To | What is needed | Needed by | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| DEP-01 | Reservation policy | Platform | Final rule table and expiry windows | 2026-12-11 | Open |
| DEP-02 | Stock feeds | Delivery promise | Confirmed feed cadence per warehouse | 2027-01-15 | Open |
| DEP-03 | Carriers | Platform | Parcelway and Northline sandbox credentials | 2027-01-22 | In progress |
| DEP-04 | Data protection | Customer testing | DPIA sign-off for beta customer contact data | 2027-03-05 | Open |
| DEP-05 | Finance systems | Launch | Horizon stock ledger reconciliation procedure agreed | 2027-03-26 | Open |
| DEP-06 | Amazon | Stock feeds | SP-API inventory quota raised to 300 calls/minute | 2027-02-05 | Requested |
| DEP-07 | Store operations | Stock feeds | Store stock feed moved from nightly to hourly batch | 2027-02-19 | In progress |
| DEP-08 | Legal | Customer messaging | Approved wording for fallback delivery estimates | 2027-04-09 | Open |
| DEP-09 | Contact centre | Launch | 60 agents trained on the new promise and escalation script | 2027-05-04 | Planned |
| DEP-10 | Northgate Fulfilment | Stock feeds | WMS maintenance window moved off 02:00–02:20 | 2027-02-12 | Open |

## The critical path

DEP-01 → build of the reservation worker → DEP-04 → beta → M5 → M6 → M7. Policy is the true
constraint: every week the bulky-item rule stays open pushes the reservation worker's completion
date by the same week, because the worker's state machine cannot be finished against an unknown
rule.

## Watch list

| Dependency | Why it worries us |
| :--- | :--- |
| DEP-06 | Amazon quota changes take up to four weeks and are outside our control |
| DEP-07 | Store stock accuracy is 91 %, so an hourly feed makes the inaccuracy more visible, not less |
| DEP-10 | A 20-minute nightly outage is currently absorbed by batch; real-time ATP cannot absorb it |

## Related

[Workstreams](./workstreams.md) · [Milestones](./milestones.md) ·
[Risk register](../governance/risk-register.md)
