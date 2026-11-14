# Webhooks

Webhooks deliver job events to your own service. Every request is signed so you can verify it
came from Meridian.

## Subscribe

`POST /api/projects/{id}/webhooks`

```json
{
  "url": "https://ci.example.com/hooks/meridian",
  "events": ["import.completed", "import.failed"],
  "secret_hint": "ci-hook"
}
```

The signing secret is returned **once** in the response. Store it in your secret manager; it
cannot be retrieved later, only rotated.

## Event Envelope

```json
{
  "id": "evt_5c10aa",
  "type": "import.completed",
  "created_at": "2026-11-14T18:22:41Z",
  "project_id": "prj_91c2",
  "data": { "job_id": "job_91", "nodes": 231, "duration_ms": 96420 }
}
```

## Headers

| Header | Value |
| :--- | :--- |
| `X-Meridian-Event` | Event type |
| `X-Meridian-Delivery` | Unique delivery id, use for deduplication |
| `X-Meridian-Signature` | `t=<unix>,v1=<hmac-sha256>` |
| `User-Agent` | `Meridian-Webhooks/1.x` |

## Verifying a Signature

The signed payload is `<timestamp>.<raw body>`. Reject timestamps older than five minutes.

```js
import { createHmac, timingSafeEqual } from "node:crypto";

export function verify(rawBody, header, secret) {
  const parts = Object.fromEntries(
    header.split(",").map((pair) => pair.split("=")),
  );
  const expected = createHmac("sha256", secret)
    .update(`${parts.t}.${rawBody}`)
    .digest("hex");
  return timingSafeEqual(Buffer.from(expected), Buffer.from(parts.v1));
}
```

Always verify against the **raw** body, before JSON parsing.

## Delivery Contract

- At-least-once; duplicates are possible, and retries reuse the same `X-Meridian-Delivery`.
- Respond with any `2xx` within 10 seconds. Anything else counts as a failure.
- Three attempts, then the delivery is marked failed and can be replayed from the CLI.

## Rotating a Secret

`POST /api/projects/{id}/webhooks/{hook_id}/rotate` issues a new secret while the old one stays
valid for 24 hours, so you can deploy the change without dropping events.

## Related
- [Notification service](../../architecture/services/notification-service.md)
- [Errors](../errors.md)
