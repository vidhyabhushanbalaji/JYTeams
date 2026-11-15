# Auth Service

The auth service is a thin module inside `meridian-api` rather than a separate deployable. It
answers one question: which tenant and user is this request for?

## Responsibilities

- Verify bearer tokens and resolve them to a tenant and user.
- Enforce per-tenant scoping on every read and write.
- Issue short-lived service tokens for CI clients.
- Publish the key set used to verify tokens without a network call.

## Token Types

| Token | Lifetime | Issued to | Notes |
| :--- | :--- | :--- | :--- |
| User token | 60 min | Browser client | Refreshed via refresh token |
| Service token | 24 h | CLI, CI | Scoped to one project by default |
| Dev token | — | Local only | Accepted only when `MERIDIAN_AUTH_MODE=dev` |

## Verification Flow

1. Extract the token from the `Authorization` header.
2. Validate signature against the cached key set (refreshed hourly, or on `kid` miss).
3. Check `exp`, then `aud` includes `meridian`.
4. Resolve `tenant_id` and `user_id`; attach them to the request context.
5. Reject with `AUTH_REQUIRED` or `AUTH_EXPIRED` before the handler runs.

Handlers never parse tokens themselves — they read the resolved context. That keeps
[Access control](../../security/access-control.md) decisions in one place.

## Key Rotation

Keys rotate every 90 days with a 24-hour overlap so cached sets keep working. The operational
steps are in [Certificate rotation](../../operations/runbooks/certificate-rotation.md).

## Failure Modes

| Symptom | Cause | Fix |
| :--- | :--- | :--- |
| 401 on every request | Clock skew over 60 s | Sync host time; see troubleshooting |
| 401 only after deploy | Cached key set stale | Restart API pods to drop the cache |
| 403 on a project you own | Token scoped to another project | Re-issue the service token |

## What This Service Does Not Do

It does not authorise individual folders. Folder-level permissions are out of scope for `1.x`;
the trade-off and the planned shape are discussed in
[Access control](../../security/access-control.md) and the [roadmap](../../product/roadmap.md).
