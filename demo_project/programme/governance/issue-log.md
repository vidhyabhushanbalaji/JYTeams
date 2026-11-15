# Issue Log

Status: Agreed · Owner: Priya Raman · Last updated: 2026-11-13

Issues are things that have already happened, as opposed to risks, which might. Anything open for
more than ten working days without movement gets escalated to the programme board automatically.

## Open

| ID | Issue | Raised | Owner | Due | Impact |
| :--- | :--- | :--- | :--- | :--- | :--- |
| ISSUE-014 | Northgate feed drops for 20 minutes during WMS maintenance | 2026-10-30 | Dan Whitcombe | 2026-11-27 | ATP shows stale stock every night at 02:00 |
| ISSUE-018 | 412 Riverside SKUs have no Atlas product match | 2026-11-04 | Ben Osei | 2026-12-04 | Bulky promise unavailable for those products |
| ISSUE-021 | Mercury order events arrive up to 90 seconds late at peak | 2026-11-10 | Dan Whitcombe | 2026-12-11 | Reservation worker sees the order after the payment webhook |
| ISSUE-023 | UAT environment holds only eight months of order history | 2026-11-12 | Aisha Bello | 2027-03-26 | Peak-volume tests will be synthetic, not replay |
| ISSUE-025 | Store stock file includes 6,400 discontinued SKUs | 2026-11-13 | Elena Vasquez | 2026-12-18 | Collection promise offers products stores cannot sell |

## ISSUE-014 in detail

StockFlow performs a WMS upgrade every night between 02:00 and 02:20 and rejects feed requests
during it. Northgate has offered to move the window to 03:30, which does not help: the problem is
not the time, it is that a failed poll is treated as an error rather than as expected silence. The
fix is to mark the window as a declared maintenance period so no staleness alert fires, and to
carry the last good snapshot through it.

## Resolved

| ID | Issue | Resolved | Resolution |
| :--- | :--- | :--- | :--- |
| ISSUE-009 | Amazon sandbox credentials revoked without notice | 2026-10-21 | New credentials issued; rotation now documented |
| ISSUE-011 | Duplicate SKUs in Atlas blocked feed mapping | 2026-10-24 | 1,180 duplicates merged by merchandising |
| ISSUE-013 | Carriers could not accept postcode-level serviceability | 2026-10-30 | Parcelway API extended; Northline provides a weekly zone file |
| ISSUE-016 | UAT database restored over test reservations | 2026-11-03 | Restore procedure requires a named request and a 24-hour notice |

## How issues differ from defects

A defect is a failure of the software against an agreed behaviour and lives in
[defect triage](../../customer-testing/uat/defect-triage.md). An issue is a real-world obstacle:
a vendor, a data gap, a contract. The distinction matters because defects have severity and a
fix, while issues need an owner and a date.

## Related

[Risk register](./risk-register.md) · [Failure and retry](../../stock-feeds/reliability/failure-and-retry.md) ·
[Feed incidents](../../stock-feeds/reliability/feed-incidents.md)
