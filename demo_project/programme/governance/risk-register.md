# Risk Register

Status: In review · Owner: Priya Raman · Last updated: 2026-11-13

Risks are scored likelihood × impact on a 1–5 scale; anything at 15 or above is reviewed by the
steering group every meeting. The register is deliberately short: a risk that has not changed in
six weeks is closed, not carried.

## Open risks

| ID | Risk | L | I | Score | Owner | Mitigation | Review |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| R-01 | Stale warehouse stock causes oversell at launch | 4 | 5 | 20 | Dan Whitcombe | Stale-threshold rule, visible degraded badge, manual hold switch | 2026-11-27 |
| R-02 | Amazon inventory API quota is not raised in time | 3 | 4 | 12 | Tom Alder | Poll at 5-minute cadence as a fallback; quota request in since 2026-10-28 | 2026-12-11 |
| R-03 | Trading and fulfilment disagree on bulky-item reservation | 4 | 4 | 16 | Sofia Mendes | Two-option paper to steering on 2026-12-03; decision needed before build | 2026-12-03 |
| R-04 | 3PL contracts do not oblige a 5-minute feed | 3 | 4 | 12 | Gavin Shore | Feed cadence added to contract variation; Northgate agreed verbally | 2027-01-15 |
| R-05 | Store stock accuracy (91 %) undermines collection promise | 4 | 3 | 12 | Elena Vasquez | Hourly feed plus a "check store" step; accuracy target 96 % by March | 2027-02-19 |
| R-06 | Bulky carrier capacity in Scotland over Easter | 3 | 3 | 9 | Gavin Shore | Northline capacity commitment for weeks 15–18 | 2027-03-05 |
| R-07 | DPIA not signed before beta recruitment | 2 | 4 | 8 | Leah Okafor | Draft DPIA circulated 2026-11-09; sign-off targeted 2027-03-05 | 2027-03-05 |
| R-08 | Mercury batch window blocks real-time availability | 3 | 3 | 9 | Ben Osei | ATP ignores Mercury's nightly stock run; event feed is the source | 2027-01-22 |
| R-09 | Key-person dependency on the integration lead | 3 | 3 | 9 | Priya Raman | Pairing from January; feed contracts written down | 2027-02-26 |
| R-10 | UAT data does not resemble live traffic | 2 | 3 | 6 | Aisha Bello | Eight months of masked order history loaded; known gap for peak volumes | 2027-04-02 |
| R-11 | Customers misread the conservative fallback date | 2 | 3 | 6 | Tom Alder | Wording approved by legal; "may arrive later" copy in fallback | 2027-04-09 |

## Closed this quarter

| ID | Risk | Closed | Why |
| :--- | :--- | :--- | :--- |
| R-12 | March launch collides with peak change freeze | 2026-09-24 | Launch moved to 2027-05-18 |
| R-13 | Parcelway has no sandbox for date calculation | 2026-10-30 | Sandbox delivered 2026-10-27 |
| R-14 | Kafka cluster licences not approved | 2026-10-09 | Approved in the October budget round |

## Top three this fortnight

R-01 and R-03 are the two that can still change the shape of the build. R-01 is being treated as
an operational problem rather than a technical one: the platform can detect stale stock, but only
fulfilment can decide what to do about it, which is why the stale-threshold rule sits in the policy
document and not in the service.

## Related

[Issue log](./issue-log.md) · [Stale stock handling](../../stock-feeds/reliability/stale-stock-handling.md) ·
[Steering group](./steering-group.md)
