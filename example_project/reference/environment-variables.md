# Environment Variables

The complete list. Anything not here is not supported, even if it happens to work.

## Core

| Variable | Default | Required | Description |
| :--- | :--- | :--- | :--- |
| `MERIDIAN_DATABASE_URL` | — | yes | Postgres connection string |
| `MERIDIAN_STORAGE_URL` | — | yes | S3-compatible endpoint and bucket |
| `MERIDIAN_STORAGE_KEY` | — | yes | Access key |
| `MERIDIAN_STORAGE_SECRET` | — | yes | Secret key |
| `MERIDIAN_MODEL_API_KEY` | — | yes | Model provider key |
| `MERIDIAN_MODEL` | `gemini-2.0-flash` | no | Model identifier, or `stub` |
| `MERIDIAN_AUTH_MODE` | `token` | no | `token` or `dev` |
| `MERIDIAN_PORT` | `8080` | no | HTTP listen port |
| `MERIDIAN_LOG_LEVEL` | `info` | no | `debug`, `info`, `warn`, `error` |

## Import and Summaries

| Variable | Default | Description |
| :--- | :--- | :--- |
| `MERIDIAN_SUMMARY_CONCURRENCY` | `4` | Parallel model calls inside one job |
| `MERIDIAN_MAX_FILE_BYTES` | `1048576` | Per-file limit for summarising |
| `MERIDIAN_MAX_UPLOAD_BYTES` | `268435456` | Whole-upload limit (256 MiB) |
| `MERIDIAN_MAX_ARCHIVE_ENTRIES` | `10000` | Zip entry cap, guards against zip bombs |
| `MERIDIAN_SKIP_EXTENSIONS` | `.png,.jpg,.jpeg,.pdf,.zip` | Stored, never summarised |
| `MERIDIAN_RETRY_ATTEMPTS` | `3` | Model call attempts before failing a node |

## Search

| Variable | Default | Description |
| :--- | :--- | :--- |
| `MERIDIAN_SEARCH_MAX_FOLDERS` | unset | Optional cap; setting it disables the fallback sweep |
| `MERIDIAN_SEARCH_FALLBACK_LIMIT` | `40` | Document count at or below which a sweep is allowed |
| `MERIDIAN_SEARCH_RANK_BATCH` | `25` | Files per ranking call |
| `MERIDIAN_SEARCH_TIMEOUT_MS` | `20000` | Per-call model timeout during a walk |

## Placement

| Variable | Default | Description |
| :--- | :--- | :--- |
| `MERIDIAN_PLACEMENT_STEP_BUDGET` | `24` | Maximum folders opened during a placement walk |
| `MERIDIAN_ADD_REQUEST_TTL_HOURS` | `24` | Lifetime of a suggestion |
| `MERIDIAN_PLACEMENT_CANDIDATES` | `5` | Candidates returned to the client |

## Operations

| Variable | Default | Description |
| :--- | :--- | :--- |
| `MERIDIAN_LOG_PROMPTS` | unset | `1` logs prompts to stdout; staging only |
| `MERIDIAN_READ_ONLY` | `0` | `1` rejects all writes, used during restores |
| `MERIDIAN_METRICS_ENABLED` | `1` | Expose `/metrics` |
| `MERIDIAN_JOB_LEASE_SECONDS` | `300` | Lease duration before a job is re-queued |
| `NODE_ENV` | `development` | `production` refuses dev auth mode |

## Precedence

Process environment beats `.env`, which beats defaults. `meridian config check` prints the
resolved values with secrets redacted.

## Related
- [Configuration guide](../getting-started/configuration.md)
- [Deployment topology](../architecture/deployment-topology.md)
