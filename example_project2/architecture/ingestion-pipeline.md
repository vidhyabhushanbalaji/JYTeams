# Ingestion Pipeline

Import is the only write path that creates a tree from scratch. It runs as a single job with
seven stages; each stage is idempotent so a retried job resumes rather than duplicates.

## Stages

| # | Stage | Output |
| :--- | :--- | :--- |
| 1 | Receive | Multipart parts or one `.zip`, stored untouched |
| 2 | Expand | Every archive entry resolved to a relative path |
| 3 | Validate | Rejected paths, unsupported names and duplicates reported |
| 4 | Prune | Empty directories dropped; leaves are folders with no child folders |
| 5 | Hash | SHA-256 per file; identical blobs share one object |
| 6 | Summarise files | One 1–2 sentence summary per markdown file |
| 7 | Describe folders | Bottom-up, each folder described from its children |

## Validation Rules

- Paths are normalised and must stay inside the upload root (`..` is rejected).
- Hidden files and `node_modules/` are skipped silently.
- Files over `MERIDIAN_MAX_FILE_BYTES` are stored but marked `summary_status = 'skipped'`.
- Non-markdown files are stored with `summary_status = 'skipped'` rather than summarised.

## Bottom-Up Description

Folders are described in reverse depth order, so a parent always sees final child
descriptions. A folder description is built from:

- the descriptions of its immediate child folders, and
- the summaries of the files it holds directly.

The root therefore describes the whole documentation set in a paragraph or two. Failures are
recorded per node and do not abort the job; the node keeps a `description_status` of `failed`
and can be retried with `meridian reindex --failed`.

## Progress and Cancellation

Each stage updates `import_jobs.processed_nodes` and `import_jobs.stage`. Clients follow these
over the job stream documented in [Projects](../api/endpoints/projects.md). Cancelling a job
stops further model calls and rolls back nodes that were never described.

## Cost Profile

Cost is dominated by stage 6 plus one call per folder in stage 7, so a repository with deep
nesting pays more per file than a flat one. The measured numbers are in
[Service level objectives](../operations/service-level-objectives.md).

Related: [ADR 0002](../decisions/0002-content-addressed-blob-storage.md) explains the hashing
step, and [Data model](./data-model.md) shows where each artefact is stored.
