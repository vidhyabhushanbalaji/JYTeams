# Documents

Documents are markdown files inside a project's tree. Meridian stores the body as a blob and
the summary in Postgres; most endpoints return metadata only.

## List a Directory

`GET /api/projects/{id}/directories/{dir_id}`

```json
{
  "path": "operations/runbooks",
  "description": "Recovery procedures for the incidents we rehearse quarterly.",
  "file_count": 3,
  "directories": [
    { "id": "dir_44a1", "name": "archived", "file_count": 2 }
  ],
  "files": [
    {
      "id": "fil_71b0",
      "name": "database-failover.md",
      "summary": "Promoting the Postgres replica after primary loss.",
      "summary_status": "done",
      "size_bytes": 4211
    }
  ]
}
```

`description` is the folder's own description, written from its children — not a concatenation
of file summaries.

## Read a Document

`GET /api/files/{file_id}` returns metadata plus a short-lived download URL:

```json
{
  "id": "fil_71b0",
  "path": "operations/runbooks/database-failover.md",
  "content_hash": "9f2c…",
  "summary": "Promoting the Postgres replica after primary loss.",
  "download_url": "https://storage.example.com/blobs/9f2c…?expires=1763575200"
}
```

The URL expires after 15 minutes. Meridian does not proxy document bodies through the API.

## Add a Single Document

Adding a file is a two-step flow: get suggestions, then commit a placement.

### 1. Suggest a Folder

`POST /api/add-requests`

```json
{
  "project_id": "prj_91c2",
  "content": "# Alert runbook\n\nHow to react when the p95 latency alert fires…",
  "path_hint": "new-alert-runbook.md"
}
```

Response:

```json
{
  "id": "add_2c91",
  "expires_at": "2026-11-15T18:20:00Z",
  "candidates": [
    { "directory_id": "dir_44a1", "path": "operations/runbooks", "relevance": 0.91,
      "reason": "Existing runbooks for on-call procedures live here." },
    { "directory_id": "dir_0001", "path": "", "relevance": 0.42, "reason": "Project root." }
  ]
}
```

The root is always offered. Suggestions live for 24 hours and can be used once.

### 2. Commit the Placement

`POST /api/add-requests/{id}/commit`

```json
{
  "directory_id": "dir_44a1",
  "name": "alert-runbook.md",
  "create_directory": null
}
```

Set `create_directory` to a folder name to create a new folder at that point instead. The file
row is written, then the folder and its ancestors are re-described bottom-up.

## Warnings

Non-markdown files and files over `MERIDIAN_MAX_FILE_BYTES` are stored with
`summary_status: "skipped"`. They appear in listings but never in search results.
