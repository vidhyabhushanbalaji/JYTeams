# Architecture Overview

Meridian is three long-running pieces and one shared datastore. Nothing else talks to Postgres
or object storage directly.

```text
                 ┌──────────────┐
  CLI / browser  │   API (HTTP) │
        ────────▶│   Fastify    │
                 └──────┬───────┘
                        │ jobs
                 ┌──────▼───────┐        ┌──────────────┐
                 │  Worker      │◀──────▶│ Model API    │
                 │  (summaries) │        └──────────────┘
                 └──────┬───────┘
          ┌─────────────┴─────────────┐
     ┌────▼─────┐              ┌──────▼──────┐
     │ Postgres │              │ Object store │
     │ (ltree)  │              │ (blobs)      │
     └──────────┘              └─────────────┘
```

## The Three Pillars

| Pillar | What it does | Deep dive |
| :--- | :--- | :--- |
| Import | Validates an uploaded folder, prunes empty directories, summarises bottom-up | [Ingestion pipeline](./ingestion-pipeline.md) |
| Placement | Walks the tree with a new document's summary and offers candidate folders | [Indexing service](./services/indexing-service.md) |
| Search | Walks the tree answering "what here?" and "where next?" per folder | [Search service](./services/search-service.md) |

## Why a Tree and Not a Vector Index

Documentation is already hierarchical — folders carry meaning. Summarising bottom-up means a
folder description is derived evidence, not a guess, and a walk can prune an entire branch with
one model call. The trade-off is that a query whose wording appears in no summary is hard to
find; the fallback sweep in [Search service](./services/search-service.md) exists for that case.

## Request Lifecycle

1. The API authenticates the caller — see [Authentication](../api/authentication.md).
2. Work is validated and written as a job row in Postgres.
3. The worker leases the job, calls the model, and commits results in one transaction.
4. Progress is pushed to the client over the job stream described in
   [Projects](../api/endpoints/projects.md).

## Component Responsibilities

| Component | Owns | Never does |
| :--- | :--- | :--- |
| API | Auth, validation, job creation, reads | Call the model for long jobs |
| Worker | Summaries, placements, re-description | Serve HTTP |
| Postgres | Tree, jobs, counts, placement history | Store document bodies |
| Object store | Markdown blobs, content-addressed | Hold queryable metadata |

Deployment units and scaling rules are in [Deployment topology](./deployment-topology.md).
