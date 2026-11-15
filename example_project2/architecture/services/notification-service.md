# Notification Service

Notifications tell you when a long job finishes and when something needs attention. They are
deliberately dull: a single dispatcher, no templating engine, no retries beyond three attempts.

## Channels

| Channel | Transport | Configured by |
| :--- | :--- | :--- |
| Webhook | HTTPS POST, signed | Project setting |
| Email | Transactional provider | Instance setting |
| Job stream | Server-sent events | Client reconnect cursor |

## Events

| Event | When | Payload highlights |
| :--- | :--- | :--- |
| `import.completed` | Import job succeeds | `project_id`, `nodes`, `duration_ms` |
| `import.failed` | Import job fails | `stage`, `error_code`, `retryable` |
| `add.suggested` | Placement candidates ready | `add_request_id`, `candidates[]` |
| `search.slow` | Search exceeded 10 s | `project_id`, `folders_visited` |

## Delivery Guarantees

At-least-once. Every delivery carries an `X-Meridian-Delivery` id and an HMAC signature over
the raw body; receivers should deduplicate on the delivery id. See
[Webhooks](../../api/endpoints/webhooks.md) for the signature scheme and verification snippet.

## Backoff

```text
attempt 1 → immediate
attempt 2 → +30 s
attempt 3 → +5 min
then give up and record notification.failed
```

A failed webhook does not fail the job that triggered it. Undelivered notifications are visible
in `meridian notifications list --failed` and can be replayed.

## What It Never Sends

- Document contents or summaries — only identifiers, counts and paths.
- Anything to a channel that has not been verified (a test ping must succeed first).
- More than one notification per job per channel.

## Related
- [Webhooks](../../api/endpoints/webhooks.md)
- [Monitoring](../../operations/monitoring.md) — alert routing for `search.slow`
