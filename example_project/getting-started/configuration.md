# Configuration

Meridian is configured through environment variables. Settings are read once at boot, so a
restart is required after any change. Precedence, highest first:

1. process environment
2. `.env` in the working directory
3. defaults baked into the image

The exhaustive list lives in [Environment variables](../reference/environment-variables.md);
this page covers the settings you are most likely to touch.

## Essential Settings

| Variable | Default | Description |
| :--- | :--- | :--- |
| `MERIDIAN_DATABASE_URL` | — | Postgres connection string, required |
| `MERIDIAN_STORAGE_URL` | — | S3-compatible endpoint, required |
| `MERIDIAN_MODEL_API_KEY` | — | Key used for summary and placement calls |
| `MERIDIAN_MODEL` | `gemini-2.0-flash` | Model identifier |
| `MERIDIAN_AUTH_MODE` | `token` | `token` or `dev`; see [Authentication](../api/authentication.md) |

## A Minimal `.env`

```dotenv
MERIDIAN_DATABASE_URL=postgresql://meridian:secret@localhost:5432/meridian
MERIDIAN_STORAGE_URL=s3://meridian-docs
MERIDIAN_STORAGE_KEY=minioadmin
MERIDIAN_STORAGE_SECRET=minioadmin
MERIDIAN_MODEL_API_KEY=<your-key>
MERIDIAN_LOG_LEVEL=info
```

## Tuning Import Behaviour

| Variable | Default | Effect |
| :--- | :--- | :--- |
| `MERIDIAN_SUMMARY_CONCURRENCY` | `4` | Parallel summary calls during import |
| `MERIDIAN_MAX_FILE_BYTES` | `1048576` | Larger markdown files are stored but not summarised |
| `MERIDIAN_SKIP_EXTENSIONS` | `.png,.jpg,.pdf` | Extensions stored without a summary |
| `MERIDIAN_RETRY_ATTEMPTS` | `3` | Retries per model call before failing the job |

## Tuning Search Behaviour

| Variable | Default | Effect |
| :--- | :--- | :--- |
| `MERIDIAN_SEARCH_MAX_FOLDERS` | unset | Optional cap on folders opened per query |
| `MERIDIAN_SEARCH_FALLBACK_LIMIT` | `40` | Projects at or below this document count get a full sweep when nothing matches |
| `MERIDIAN_SEARCH_RANK_BATCH` | `25` | Files per ranking call when the result log is large |

## Dev Mode

`MERIDIAN_AUTH_MODE=dev` trusts an `X-Debug-User` header and skips token verification. It is
rejected when `NODE_ENV=production`. Never enable it on a shared instance.

## Validating Configuration

```bash
meridian config check
```

The command prints the resolved values (secrets redacted) and exits non-zero if anything
required is missing.
