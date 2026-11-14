# Certificate Rotation

TLS certificates for the ingress and the JWKS signing keys both rotate. Neither requires downtime
if the overlap window is respected.

## What Expires

| Certificate | Lifetime | Owner | Renewal |
| :--- | :--- | :--- | :--- |
| Ingress TLS | 90 days | Platform | Automatic, ACME |
| JWKS signing key | 90 days | Auth module | Manual, this runbook |
| Webhook signing secret | 90 days | Tenant | Tenant admin, self-service |

The alert `CertificateExpiringSoon` fires at 14 days. Automatic renewal handles ingress; the
manual step is the signing key, which needs a coordinated deploy.

## Ingress TLS

```bash
kubectl describe certificate meridian-tls | grep -E 'Not After|Renewal Time'
kubectl cert-manager renew meridian-tls
```

Cert-manager should have done this already. If the certificate is stuck in `Pending`, check the
ACME challenge: a stale DNS record is the usual cause.

## JWKS Signing Key

Rotation is two releases, 24 hours apart, so cached key sets never see an unknown `kid`.

### Release 1 — publish the new key

```bash
meridian keys rotate --publish-only --kid k-2026-02
kubectl rollout restart deploy/meridian-api
curl -s https://api.meridian.example.com/.well-known/meridian-jwks.json | jq '.keys[].kid'
```

Both keys must appear. New tokens are signed with the new key immediately; the old key remains
published for verification.

### Release 2 — retire the old key (next day)

```bash
meridian keys retire --kid k-2026-01
kubectl rollout restart deploy/meridian-api
```

Confirm the retired `kid` is gone from the JWKS document and that no 401 spikes appear in the
next ten minutes.

## Verifying Nothing Broke

| Check | Expected |
| :--- | :--- |
| `meridian auth test` | `ok` using a freshly issued token |
| `AUTH_INVALID` rate | Unchanged from baseline |
| CLI sessions | Still valid; no forced re-login |

A burst of `AUTH_INVALID` immediately after release 2 means a cache is still serving the retired
key — restart the API pods to drop it.

## If You Miss the Overlap Window

Publish the old key again with `meridian keys republish --kid <old>`, wait for caches to refresh
(up to 60 minutes), then retire it properly. Do not re-sign old tokens.

## Related
- [Auth service](../../architecture/services/auth-service.md)
- [Authentication](../../api/authentication.md)
