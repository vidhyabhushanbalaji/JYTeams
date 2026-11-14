# Local Development

The full stack runs locally with one compose file. Everything below assumes the repository is
checked out and `pnpm install` has been run at the root.

## Start the Stack

```bash
docker compose -f deploy/compose.local.yml up -d postgres minio
pnpm --filter @meridian/api migrate
pnpm dev            # api + worker + web, watched
```

| Service | URL |
| :--- | :--- |
| API | <http://localhost:8080> |
| Web client | <http://localhost:5173> |
| MinIO console | <http://localhost:9001> |
| Postgres | `postgresql://meridian:meridian@localhost:5432/meridian` |

## Dev Authentication

Set `MERIDIAN_AUTH_MODE=dev` in `.env` and skip tokens entirely:

```bash
curl http://localhost:8080/api/projects -H "X-Debug-User: local-dev"
```

The CLI picks up the same mode when `MERIDIAN_DEV=1` is exported. Never enable dev mode on a
host other engineers can reach.

## Seeding a Project

```bash
pnpm seed:handbook      # imports ./fixtures/handbook as project "handbook"
```

The fixture is a 40-file tree with one deliberately awkward folder so placement has something
interesting to do.

## Working With the Model

Without a key, set `MERIDIAN_MODEL=stub`. The stub returns deterministic summaries derived from
the filename and first heading, so tests and UI work do not need network access or spend.

To inspect a real prompt, log it once:

```bash
MERIDIAN_LOG_PROMPTS=1 pnpm --filter @meridian/worker dev
```

Prompt text is redacted automatically when `MERIDIAN_LOG_PROMPTS` is unset.

## Database Changes

1. Write a migration in `deploy/migrations` with the next sequential number.
2. Apply it locally: `pnpm --filter @meridian/api migrate`.
3. Never edit a migration that has been merged — forward-only.
4. Reset when things get messy: `pnpm --filter @meridian/api migrate:reset`.

## Common Snags

| Symptom | Fix |
| :--- | :--- |
| `extension "ltree" is not available` | Use the compose Postgres image, not a stripped build |
| Port 5432 already in use | `MERIDIAN_PG_PORT=5433 docker compose ... up` |
| Worker idle, jobs queued | `MERIDIAN_AUTH_MODE` differs between api and worker |
| Blob upload 403 | MinIO bucket created? `pnpm storage:init` |

Anything not covered here belongs in [Troubleshooting](./troubleshooting.md).
