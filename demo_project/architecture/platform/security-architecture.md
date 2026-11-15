# Security Architecture

Status: Draft · Owner: Nadia Kerr · Last updated: 2026-11-13

The platform holds no customer names or addresses, which makes it a smaller target than the systems
around it. What it does hold is stock truth, order IDs and postcodes, and it can move stock, so its
integrity matters more than its confidentiality.

## Assets

| Asset | Sensitivity | Impact of compromise |
| :--- | :--- | :--- |
| Stock snapshot | Internal | Wrong availability, oversell |
| Reservation records | Internal | Stock locked or released wrongly |
| Promises | Internal plus postcode district | Customer expectation and trust |
| Feed credentials | Secret | Ability to inject false stock |
| Admin console | High | Holds, policy changes |

## Controls

| Control | Implementation |
| :--- | :--- |
| Identity | SSO for humans, service identities for services |
| Service-to-service | mTLS internally |
| Feed authentication | Signed requests, rotating credentials |
| Admin actions | SSO plus MFA, named user, audited |
| Secrets | Managed store, no secrets in code or config |
| Network | Private subnets, allow-lists for warehouse sources |
| Data in transit | TLS 1.2+ externally, mTLS internally |
| Data at rest | Encrypted volumes and buckets |

## Authorisation

| Actor | May |
| :--- | :--- |
| Storefront | Quote and read availability |
| Marketplace adapter | Quote and read availability |
| Reservation worker | Reserve and release |
| DPS | Quote availability |
| Fulfilment user | Hold and release via console |
| Policy owner | Change business keys |
| Platform engineer | Deploy, read metrics, no business data |

The storefront cannot create a reservation. That is the most important authorisation rule in the
system: a compromised storefront can read stock, not consume it.

## Privacy by design

| Principle | Implementation |
| :--- | :--- |
| Data minimisation | No name, email or address stored |
| Purpose limitation | Postcode used for serviceability only |
| Storage limitation | 90-day platform retention, 30-day promises |
| Pseudonymisation | Postcode district plus hash in logs |
| Transparency | Help-centre page on how dates are calculated |

The postcode is the only customer-derived field the platform keeps. Retaining it is necessary because
serviceability is the product; retaining more is not.

## Threats and mitigations

| Threat | Mitigation |
| :--- | :--- |
| Forged feed batch | HMAC signature plus timestamp window |
| Replayed batch | Batch ID plus cursor check |
| Credential reuse across environments | Separate secret stores per environment |
| Insider release of stock | Reason code plus daily report |
| Console misuse | MFA, audit, four-eyes for policy changes over a threshold |
| Dependency vulnerability | Daily scanning, 7-day remediation for high |
| Log leakage | Automated scan for patterns before release |

## Third parties

| Party | Access | Contract |
| :--- | :--- | :--- |
| Cortex Partners | Code, UAT, staging | NDA, least privilege, no production data |
| Northgate | Their WMS only | Contract schedule, no access to platform |
| Riverside | Their WMS only | Same |
| Carriers | Their APIs | API keys, scoped |
| Penetration tester | UAT | Rules of engagement, supervised |

## What is not yet good enough

| Gap | Risk | Plan |
| :--- | :--- | :--- |
| Riverside static API key | Credential compromise | OAuth migration, February |
| No WAF in front of the admin console | Console exposure | WAF rule set before UAT |
| Kafka topic authorisation is coarse | A service can read more than it needs | Per-topic ACLs before launch |
| No automated secret rotation | Stale credentials | Rotation runbook, manual today |

These are tracked as security findings, not as risks, because they have owners and dates.

## Related

[Security testing](../../customer-testing/non-functional/security-testing.md) ·
[Feed authentication](../../stock-feeds/protocol/authentication.md) ·
[System context](../system-context.md)
