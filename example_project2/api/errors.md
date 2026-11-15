# Errors

Errors are always JSON with a stable machine-readable `code`. Clients should branch on `code`,
never on the human-readable `message`.

## Error Envelope

```json
{
  "error": {
    "code": "PROJECT_NOT_FOUND",
    "message": "No project with id prj_91c2",
    "details": { "project_id": "prj_91c2" },
    "request_id": "req_7f3a91"
  }
}
```

Include `request_id` in support requests — it is the only reliable way to find the trace.

## Codes

| HTTP | Code | Retryable | Meaning |
| :--- | :--- | :--- | :--- |
| 400 | `VALIDATION_FAILED` | no | Malformed body or query |
| 400 | `UNSUPPORTED_ARCHIVE` | no | Zip could not be expanded safely |
| 401 | `AUTH_REQUIRED` / `AUTH_EXPIRED` / `AUTH_INVALID` | sometimes | See [Authentication](./authentication.md) |
| 403 | `SCOPE_DENIED` | no | Token lacks the project |
| 404 | `PROJECT_NOT_FOUND` | no | Unknown project id |
| 404 | `FILE_NOT_FOUND` | no | Unknown path in the tree |
| 409 | `IMPORT_IN_PROGRESS` | yes | One import per project at a time |
| 409 | `ADD_REQUEST_CONSUMED` | no | Placement already used |
| 410 | `ADD_REQUEST_EXPIRED` | no | Placement older than 24 hours |
| 413 | `UPLOAD_TOO_LARGE` | no | Over `MERIDIAN_MAX_UPLOAD_BYTES` |
| 422 | `TREE_INVARIANT_VIOLATION` | no | Resulting tree would break the model |
| 429 | `RATE_LIMITED` | yes | Back off using `Retry-After` |
| 500 | `INTERNAL` | yes | Unexpected server fault |
| 503 | `DEPENDENCY_UNAVAILABLE` | yes | Postgres or object store unreachable |
| 504 | `MODEL_TIMEOUT` | yes | Model call exceeded the deadline |

## Retry Guidance

Retry only codes marked retryable, with exponential backoff and jitter, at most five attempts.
Do not retry `409` and `429` before honouring `Retry-After`.

## Partial Failures

Import and placement can succeed with warnings. Those appear on the resource, not as errors:

```json
{
  "id": "prj_91c2",
  "status": "succeeded",
  "warnings": [
    { "path": "assets/diagram.png", "code": "SKIPPED_NOT_MARKDOWN" }
  ]
}
```

## Related
- [Rate limits](./rate-limits.md)
- [Troubleshooting](../guides/troubleshooting.md)
