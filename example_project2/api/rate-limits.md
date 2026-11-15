# Rate Limits

Limits are per tenant and per endpoint family, counted in a sliding one-minute window. They
protect the model budget, not the web tier — the API itself is cheap.

## Defaults

| Family | Endpoints | Limit |
| :--- | :--- | :--- |
| Reads | `GET` on projects, directories, files | 600 / min |
| Writes | `POST`, `PATCH`, `DELETE` | 120 / min |
| Search | `POST /api/search` | 30 / min, 4 concurrent |
| Placement | `POST /api/add-requests` | 20 / min |
| Imports | `POST /api/projects/:id/import` | 3 / hour, 1 concurrent per project |

## Response Headers

```text
X-RateLimit-Limit: 30
X-RateLimit-Remaining: 27
X-RateLimit-Reset: 1763571660
Retry-After: 12
```

`Retry-After` appears only on `429` responses and is in seconds. It is always present — do not
compute your own backoff without it.

## Exceeding a Limit

```json
{
  "error": {
    "code": "RATE_LIMITED",
    "message": "Search limit exceeded for tenant_acme",
    "details": { "family": "search", "reset_at": "2026-11-14T18:41:00Z" },
    "request_id": "req_c31b02"
  }
}
```

## Recommended Client Behaviour

1. Read `X-RateLimit-Remaining` on every response and slow down below 10%.
2. On `429`, wait exactly `Retry-After` plus 0–500 ms jitter.
3. Batch reads instead of polling in a loop; use the job stream for progress.
4. For bulk imports, use one archive upload rather than many small ones.

## Raising Limits

Tenant admins can request a quota increase; the request is reviewed against model spend, not
traffic. Quota changes are recorded in the [changelog](../changelog/2026-11.md).

## Related
- [Errors](./errors.md)
- [Search endpoint](./endpoints/search.md)
