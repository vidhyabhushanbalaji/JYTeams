# Cutover Plan

Status: Draft · Owner: Marcus Feld · Last updated: 2026-11-13

How we move from the old promise to the new one without a gap. The cutover is per channel, reversible
within 45 minutes, and rehearsed twice before it happens for real.

## The sequence (website, 2027-05-18)

| Time | Step | Owner | Duration | Reversible |
| :--- | :--- | :--- | :--- | :--- |
| T-24 h | Freeze configuration changes | Nadia Kerr | — | Yes |
| T-24 h | Final feed check, all five sources fresh | Dan Whitcombe | 30 min | Yes |
| T-2 h | Enable the new promise for 1 % of traffic | Tom Alder | 5 min | Yes |
| T-1 h | Review 1 % metrics; proceed or stop | Priya Raman | 15 min | Yes |
| T-30 m | Scale to production capacity | Nadia Kerr | 10 min | Yes |
| T-0 | Enable for 100 % of website traffic | Tom Alder | 5 min | Yes |
| T+15 m | Verify quotes, reservations, errors | Nadia Kerr | 15 min | Yes |
| T+1 h | Verify first orders and promises | Aisha Bello | 30 min | Yes |
| T+4 h | Review accuracy signals and contacts | Marcus Feld | 30 min | Yes |
| T+24 h | Declare website live or roll back | Priya Raman | — | — |

Times are relative to 09:00 on 18 May, chosen deliberately: mid-morning on a Tuesday, not at
midnight, because a cutover at midnight means the first people to see a problem are customers in the
morning rush.

## Why 1 % first

The 1 % step is a real traffic split, not a test. It exposes the platform to genuine product pages,
genuine postcodes and genuine order combinations for an hour while the blast radius stays small. The
October rehearsal found two defects in that hour that no synthetic test had found.

## What changes at cutover

| Component | Before | After |
| :--- | :--- | :--- |
| Product page date | Stock flag only | Promise from DPS |
| Checkout services | All shown, some withdrawn | Filtered by serviceability |
| Stock source | Mercury nightly extract | ATP live from feeds |
| Reservations | None | Soft reservation at authorisation |
| Store collection | Store file flag | Store reservation and task |
| Contact centre screen | Mercury date | DPS date plus fallback reason |

Mercury keeps routing and dispatch. What changes is where availability and dates come from.

## What does not change at cutover

Marketplaces (a week later), wholesale (two weeks later), store collection (three weeks later),
Mercury routing, Horizon ledger, carrier contracts, and the returns process. Keeping the first
cutover narrow is the main reason it is believable.

## Pre-cutover checks

- [ ] All five feeds fresh for 60 minutes
- [ ] Carrier sandboxes replaced by production credentials
- [ ] Reservation worker running at production scale for 24 hours
- [ ] Contact centre briefed and roster confirmed
- [ ] Rollback tested in staging within the last 7 days
- [ ] Monitoring dashboards live with correct thresholds
- [ ] War room staffed with named people, not a channel
- [ ] Comms sent to stores, carriers and internal teams

## War room

| Role | Person | Location |
| :--- | :--- | :--- |
| Launch lead | Marcus Feld | Head office |
| Platform | Nadia Kerr | Head office |
| Feeds | Dan Whitcombe | Remote, dialled in |
| Product | Tom Alder | Head office |
| Support | Contact centre lead | Contact centre |
| Programme | Priya Raman | Head office |

The war room has a shared screen with four panels: availability latency, reservation rate, promise
fallback share, and contacts per 100 orders. Nothing else is on the screen.

## Related

[Timeline](./timeline.md) · [Rollback plan](../rollback/rollback-plan.md) ·
[Go/no-go checklist](./go-no-go-checklist.md)
