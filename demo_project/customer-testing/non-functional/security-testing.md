# Security Testing

Status: Draft · Owner: Nadia Kerr · Last updated: 2026-11-13

Security testing for a platform that holds postcodes, order data and five warehouse credentials. The
threat model is small and specific, which makes testing it practical rather than theoretical.

## Scope

| In scope | Out of scope |
| :--- | :--- |
| ATP, DPS, ingestor, reservation worker | Mercury and Horizon internals |
| Feed endpoints and authentication | Carrier systems |
| Storefront integration points | Marketplace platforms |
| Logging and data retention | Corporate network |
| Secrets handling | Physical security |

## What we test

| Test | Method | Frequency | Owner |
| :--- | :--- | :--- | :--- |
| Static analysis | Pipeline, on every commit | Continuous | Engineering |
| Dependency scanning | Pipeline, nightly | Daily | Nadia Kerr |
| Dynamic scanning | OWASP ZAP against UAT | Weekly from March | Nadia Kerr |
| Authentication and authorisation | Manual, per endpoint | Before UAT | Dan Whitcombe |
| Injection and input handling | Manual plus fuzzing of feed payloads | Before UAT | Nadia Kerr |
| Rate limiting and abuse | Scripted load beyond limits | Before UAT | Nadia Kerr |
| Penetration test | External firm, 5 days | March 2027 | Priya Raman |
| Secrets review | Manual, all environments | Before each release | Nadia Kerr |

## The threats that matter

| Threat | Test | Expected result |
| :--- | :--- | :--- |
| Forged feed data | Replay a signed batch with a modified body | Signature rejected, alert raised |
| Stolen feed credential | Use a rotated-but-not-revoked key | Accepted only inside the overlap window |
| Enumeration of stock | Script 10,000 SKU reads | Rate limited, no pricing leak |
| Reservation spam | Create reservations without orders | Only the reservation worker can reserve |
| Postcode harvesting | Query many postcodes | Throttled, district-only logging |
| Log leakage | Search logs for postcodes and tokens | None found |
| Injection via feed fields | Fuzz SKU and location fields | Rejected, no execution |
| Cross-channel impersonation | Call marketplace endpoints as website | 403 |

The fourth row is the important design control: the storefront physically cannot create a
reservation, so a compromised storefront degrades to reading stock rather than consuming it.

## Data protection checks

| Check | Requirement |
| :--- | :--- |
| Postcode in logs | District plus hash only |
| Order data retention | 90 days in logs, 7 years in Mercury |
| Beta consent records | Stored, auditable, withdrawable |
| Test data | Masked, deleted after hypercare |
| Access to production data | Named individuals, MFA, logged |

## Findings process

| Severity | Definition | Response |
| :--- | :--- | :--- |
| Critical | Data exposure or authentication bypass | Fix before any launch activity |
| High | Privilege escalation or credential leak | Fix before UAT exit |
| Medium | Information disclosure, weak limiting | Fix before go-live |
| Low | Hardening | Hypercare backlog |

Findings are tracked like defects and share the same triage rhythm. A critical finding stops the
launch, with no discretion, and that rule is written down so it cannot be negotiated in May.

## Current position

| Item | Status |
| :--- | :--- |
| Static analysis | Clean |
| Dependency scan | 2 medium, both accepted with compensating controls |
| ZAP baseline | 4 medium (headers, cookies), fixed |
| Auth review | Complete, one finding open (token lifetime) |
| Pen test | Booked for 2027-03-08 |
| Secrets | One static key in production (Riverside), migration booked |

## Related

[Security architecture](../../architecture/platform/security-architecture.md) ·
[Feed authentication](../../stock-feeds/protocol/authentication.md) ·
[Change control](../../programme/governance/change-control.md)
