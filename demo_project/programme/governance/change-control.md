# Change Control

Status: Agreed · Owner: Priya Raman · Last updated: 2026-11-13

What counts as a change, who approves it, and when the programme refuses to accept one at all.

## What counts as a change

- Scope: a new channel, warehouse, carrier, or a promise we did not plan to make.
- Date: anything that moves M2–M9.
- Policy: any edit to a rule in the reservation rule table after 2027-01-11.
- Data: a new field leaving the platform, or a new retention period.
- Launch order: swapping which channel goes first.

Documentation edits inside a workstream, test data changes and defect fixes are not changes. They
are normal work and stay with the workstream lead.

## Thresholds

| Size | Approver | Turnaround |
| :--- | :--- | :--- |
| Up to 5 days of effort, no date impact | Programme lead | 2 working days |
| 5–15 days, or a workstream replan | Programme board (leads) | Weekly board |
| Over 15 days, or any milestone impact | Steering group | Next scheduled meeting |

## The request

A change request is one page: what changes, why now, what it costs in effort and calendar, what it
displaces, and what happens if we do not do it. Requests without the "displaces" line are returned
unread, because the programme has no spare capacity to absorb anything.

## Current requests

| ID | Request | Raised | Size | Status |
| :--- | :--- | :--- | :--- | :--- |
| CR-004 | Add a 6-hour stock buffer for bank holiday weekends | 2026-10-30 | 8 days | Approved |
| CR-007 | Store stock feed at hourly cadence instead of nightly | 2026-11-04 | 11 days | Approved |
| CR-008 | Show a stock count band ("only 3 left") on product pages | 2026-11-06 | 14 days | Rejected (not this release) |
| CR-009 | Email notification when a promised date changes | 2026-11-10 | 9 days | In review |
| CR-010 | Include Northern Ireland in Parcelway next-day scope | 2026-11-12 | 6 days | In review |

## Freeze windows

| Window | Dates | Rule |
| :--- | :--- | :--- |
| Pre-UAT code freeze | 2027-03-19 to 2027-04-05 | Fixes only, no new behaviour |
| Launch freeze | 2027-05-11 to 2027-06-08 | No change without the sponsor's written approval |
| Peak freeze | 2027-10-25 to 2028-01-08 | Stock, promise and carrier changes only with a go/no-go |

## Why CR-008 was rejected

The "only 3 left" band is a trading idea, not a stock-visibility one, and it needs merchandising
rules we do not have. It was deferred to the post-peak roadmap rather than squeezed into April,
where it would have competed with UAT fixes for the same two engineers.

## Related

[Decision rights](./decision-rights.md) · [Milestones](../plan/milestones.md) ·
[Change freeze](../../launch-readiness/cutover/change-freeze.md)
