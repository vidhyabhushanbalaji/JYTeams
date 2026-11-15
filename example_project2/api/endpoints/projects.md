# Projects

A project is the container for one documentation tree. All other resources are reachable only
through a project, and every request is scoped to the caller's tenant.

## Create a Project

`POST /api/projects`

```json
{
  "name": "handbook",
  "description": "Engineering handbook for the platform team",
  "visibility": "tenant"
}
```

Returns `201` with the project, including `id` and `root_directory_id`.

## List Projects

`GET /api/projects?limit=25&cursor=...`

```json
{
  "items": [
    { "id": "prj_91c2", "name": "handbook", "documents": 412, "status": "ready" }
  ],
  "next_cursor": null
}
```

Pagination is cursor-based; `limit` defaults to 25 and maxes at 100.

## Import a Tree

`POST /api/projects/{id}/import`

Accepts either loose multipart parts with relative filenames or a single `file` part containing
a `.zip`. Optional query parameters:

| Parameter | Default | Effect |
| :--- | :--- | :--- |
| `prune_empty` | `true` | Drop directories with no files anywhere beneath |
| `replace` | `false` | Replace the existing tree instead of adding to it |
| `notify` | `true` | Send `import.completed` when done |

```bash
curl -X POST "http://localhost:8080/api/projects/prj_91c2/import?replace=true" \
  -H "Authorization: Bearer $MERIDIAN_TOKEN" \
  -F "file=@docs.zip"
```

Only one import may run per project; a second returns `409 IMPORT_IN_PROGRESS`.

## Follow Progress

`GET /api/projects/{id}/jobs/{job_id}/events` returns server-sent events:

```text
event: stage
data: {"stage":"summarise_files","processed_nodes":118,"total_nodes":231}

event: done
data: {"status":"succeeded","nodes":231,"duration_ms":96420}
```

Reconnect with `Last-Event-ID` to resume without replaying the whole stream.

## Get a Project

`GET /api/projects/{id}` returns counts, timestamps and the root description:

```json
{
  "id": "prj_91c2",
  "name": "handbook",
  "documents": 412,
  "directories": 38,
  "root_summary": "An engineering handbook covering onboarding, services and on-call practice."
}
```

## Delete a Project

`DELETE /api/projects/{id}` removes rows, then blobs referenced only by that project. Blobs
shared with another project are kept — see
[Content-addressed storage](../../decisions/0002-content-addressed-blob-storage.md).

## Related
- [Documents](./documents.md)
- [Import job stages](../../architecture/ingestion-pipeline.md)
