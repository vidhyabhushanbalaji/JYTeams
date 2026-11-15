# Environments

Status: Agreed · Owner: Nadia Kerr · Last updated: 2026-11-13

Six environments, and the differences between them are the most common source of test surprises.
This document exists so that "it worked in UAT" can be checked against a list rather than argued
about.

## The environments

| Environment | Purpose | Data | Feeds | Carriers |
| :--- | :--- | :--- | :--- | :--- |
| Local | Developer machines | Synthetic | Simulator | Mocks |
| CI | Automated tests | Synthetic | Simulator | Mocks |
| Integration | Feed and carrier development | Replay fixtures | Simulator, replay | Sandboxes |
| UAT | Business acceptance | Masked October 2026 orders | Replay and simulator | Sandboxes |
| Staging | Pre-production rehearsal | Masked, refreshed weekly | Sandboxes, one live read-only | Sandboxes |
| Production | Live | Real | Real | Real |

Staging has one live read-only feed (Midlands DC) so that the shape of real data is exercised without
writing anything into a warehouse system. Nothing else is live before production.

## What UAT contains

| Component | Version | Note |
| :--- | :--- | :--- |
| ATP service | Release candidate | Deployed from the UAT tag |
| DPS | Release candidate | Carrier sandboxes |
| Ingestor | Release candidate | Replay plus simulator |
| Mercury | 8.4.2 plus UAT hotfix | Differences from production documented |
| Horizon | Sandbox | Read-only |
| Store file | 41,000 rows from 2026-11-01 | Real store codes, scaled quantities |

The Mercury hotfix is the one known drift: production lacks a fix that UAT has, and it changes the
dispatch event's timestamp by up to 4 seconds. It is scheduled into production on 2027-02-26.

## Data refresh

| Environment | Refresh | Method |
| :--- | :--- | :--- |
| UAT | Weekly, Sunday | Restore masked snapshot |
| Staging | Weekly, Wednesday | Restore masked snapshot |
| Integration | On demand | Reload fixtures |

A restore requires a named request and 24 hours notice, after ISSUE-016, where a restore ran over an
afternoon of reservations and invalidated a day of testing.

## Access

| Environment | Who | Authentication |
| :--- | :--- | :--- |
| Local, CI | Engineering | None |
| Integration | Engineering, QA | SSO |
| UAT | Business teams, QA, engineering | SSO plus role |
| Staging | Engineering, SRE | SSO plus MFA |
| Production | SRE, on-call, approvers | SSO, MFA, break-glass |

Beta customers are on production, which is not an accident: a beta on a test environment proves
nothing about a real order, and Tom Alder argued successfully that the risk is lower than the risk of
learning nothing.

## What cannot be simulated

| Thing | Why | Mitigation |
| :--- | :--- | :--- |
| Real carrier capacity | Sandboxes accept everything | Capacity tests use recorded responses |
| Peak traffic | UAT has no real product-page load | Load test with synthetic traffic |
| Real customer behaviour | Scripts are always more patient | Beta |
| Marketplace algorithms | Amazon sandbox is not production | Conservative marketplace buffer |
| Warehouse physical picking | No test warehouse | Beta plus pilot stores |

## Related

[Test data](./test-data.md) · [Performance testing](../non-functional/performance-testing.md) ·
[Cutover plan](../../launch-readiness/cutover/cutover-plan.md)
