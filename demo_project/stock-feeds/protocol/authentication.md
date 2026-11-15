# Feed Authentication

Status: Draft · Owner: Nadia Kerr · Last updated: 2026-11-06

How the platform proves who it is to five warehouse systems and how they prove themselves to us.
Four of the five still use static credentials, which is the largest security debt in this workstream.

## Today's position

| Source | Their mechanism | Our mechanism | Rotation |
| :--- | :--- | :--- | :--- |
| Midlands DC | Internal network, IP allow-list | Service account, SQL | Annual, manual |
| Glasgow DC | Internal network, IP allow-list | Service account, SQL | Annual, manual |
| Northgate | Static API key in header | Shared secret on our endpoint | Annual, manual |
| Riverside | Static API key plus IP allow-list | Shared secret | Never since 2022 |
| Store network | SFTP key pair | SFTP key pair | Never since 2021 |

## The target

| Source | Target mechanism | Owner | When |
| :--- | :--- | :--- | :--- |
| Midlands, Glasgow | Kerberos or mTLS on the API wrapper | Dan Whitcombe | Before UAT |
| Northgate | OAuth client credentials, 60-minute tokens | Dan Whitcombe | 2027-02 |
| Riverside | OAuth client credentials (vendor supports it) | Dan Whitcombe | 2027-02 |
| Store network | SFTP key pair, rotated annually from 2027 | Elena Vasquez | 2027-01 |

OAuth on both 3PLs was in the contract variation, not a separate request, because a static key with
no rotation is a finding in any security review and would block the launch gate.

## How a feed request is authenticated

```text
POST /feeds/{source}/batch
Authorization: Bearer <token>
X-Feed-Signature: sha256=<hmac of body, timestamp>
X-Feed-Timestamp: 2026-11-13T09:41:00Z
```

| Check | Rejection |
| :--- | :--- |
| Token valid and not expired | 401 |
| Timestamp within 5 minutes of our clock | 401 |
| Signature matches the body | 401 |
| Source IP inside the allow-list (where used) | 403 |
| Source permitted to write this location | 403 |

Rejected requests are logged with the reason but never with the body, because bodies contain stock
and, in the store file, sale information.

## Secrets handling

| Secret | Stored in | Who can read |
| :--- | :--- | :--- |
| 3PL client secrets | Secret manager, per environment | Platform team |
| SFTP private key | Secret manager | Platform team, store operations |
| Signing keys | Secret manager, rotated every 90 days | Platform team |
| Mercury service account | Secret manager | Platform team |

No credential is in a repository, a configuration file or a document. The `.env.example` pattern used
elsewhere in the product lists names, never values, and that rule applies here too.

## Rotation without a gap

A 24-hour overlap: the new credential is issued, both are accepted, the source is moved, then the
old one is revoked. This is the same overlap pattern used for the marketplace webhook rotation in
2026, and it exists because Riverside's 2022 key rotation caused a four-hour stock outage when the
old key was revoked first.

## What is still weak

| Weakness | Risk | Mitigation |
| :--- | :--- | :--- |
| Riverside key unchanged since 2022 | Credential leak | OAuth migration in February |
| Store SFTP has no replay protection | Duplicate file applied twice | File timestamp check at ingest |
| Internal IP allow-list assumes the network boundary holds | Lateral movement | mTLS before UAT |
| No per-source rate limit | A runaway loop looks like a stock event | Per-source quota, 10× normal |

## Related

[Feed contracts](./feed-contracts.md) · [Security architecture](../../architecture/platform/security-architecture.md) ·
[Security testing](../../customer-testing/non-functional/security-testing.md)
