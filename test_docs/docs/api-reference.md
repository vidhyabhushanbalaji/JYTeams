# API Reference

Base URL: `https://api.pulse.example.com/v1`

## Authentication
Include your tenant key in the request header:
`Authorization: Bearer <YOUR_API_KEY>`

---

## Endpoints

### `POST /events`
Ingests a single telemetry event.

**Request Body:**
```json
{
  "event": "user.signup",
  "timestamp": "2026-11-14T18:00:00Z",
  "properties": {
    "plan": "pro",
    "region": "eu-west-2"
  }
}
```

**Responses:**
- `202 Accepted` — Event queued for processing.
- `400 Bad Request` — Invalid payload schema.
- `429 Too Many Requests` — Rate limit exceeded.