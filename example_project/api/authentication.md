# Authentication

Every endpoint except `/health` requires a bearer token. Tokens identify a tenant and a user;
all data access is scoped to the tenant automatically.

## Sending a Token

```bash
curl http://localhost:8080/api/projects \
  -H "Authorization: Bearer $MERIDIAN_TOKEN"
```

A missing or malformed header returns `401` with code `AUTH_REQUIRED`. An expired token returns
`401` with code `AUTH_EXPIRED` — refresh and retry once.

## Obtaining a Token

| Client | How |
| :--- | :--- |
| CLI | `meridian login` opens the browser and stores a refreshed token |
| Browser | OAuth-style redirect flow, token kept in memory |
| CI | `meridian token create --project handbook --ttl 24h` |

Service tokens are scoped to a single project unless `--project '*'` is passed by a tenant
admin. Prefer the narrowest scope that works.

## Token Claims

```json
{
  "sub": "user_8f21",
  "tenant_id": "tenant_acme",
  "scope": "project:handbook",
  "aud": "meridian",
  "exp": 1763571600,
  "kid": "k-2026-11"
}
```

## Verifying Without a Round Trip

The public key set is served at `GET /.well-known/meridian-jwks.json`. Keys rotate every 90
days with a 24-hour overlap; cache by `kid` and refetch on a miss.

## Development Mode

With `MERIDIAN_AUTH_MODE=dev`, the API trusts an `X-Debug-User` header instead of a token:

```bash
curl http://localhost:8080/api/projects -H "X-Debug-User: local-dev"
```

Dev mode is refused when `NODE_ENV=production`. It exists so local work and integration tests do
not need a token issuer — see [Local development](../guides/local-development.md).

## Common Errors

| Status | Code | Meaning |
| :--- | :--- | :--- |
| 401 | `AUTH_REQUIRED` | Header missing or not `Bearer` |
| 401 | `AUTH_EXPIRED` | Token past `exp` |
| 401 | `AUTH_INVALID` | Signature or audience mismatch |
| 403 | `SCOPE_DENIED` | Token not scoped to the requested project |

All codes and their retry semantics are listed in [Errors](./errors.md).
