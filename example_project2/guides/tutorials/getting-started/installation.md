# Installation

Meridian ships as a single container image plus a CLI. You need somewhere to run Postgres 16+
and an object store; the compose file below gives you both.

## Prerequisites

| Requirement | Minimum | Notes |
| :--- | :--- | :--- |
| Docker | 24.x | Or a container runtime of your choice |
| PostgreSQL | 16 | `ltree` and `pg_trgm` extensions must be installable |
| Object storage | S3-compatible | MinIO is bundled in the compose file |
| Model API key | — | Used for summaries and placement |

## Option 1: Docker Compose

```bash
git clone https://github.com/example/meridian.git
cd meridian
cp .env.example .env          # set MERIDIAN_MODEL_API_KEY
docker compose up -d
```

The API becomes reachable at `http://localhost:8080`. Migrations run automatically on boot;
to run them by hand use `meridian migrate`.

## Option 2: From Source

```bash
pnpm install
pnpm --filter @meridian/api build
pnpm --filter @meridian/api start
```

## Install the CLI

```bash
npm install -g @meridian/cli
meridian --version
```

## Verify the Install

```bash
curl -s http://localhost:8080/health
# {"status":"ok","database":"ok","storage":"ok"}
```

If `database` or `storage` is not `ok`, jump to [Troubleshooting](../guides/troubleshooting.md).

## Next Steps
- Read [Configuration](./configuration.md) for every supported environment variable.
- Import your first set of documents with the [Quick Start](./quickstart.md).
