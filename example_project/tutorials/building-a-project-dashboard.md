# Tutorial: Building a Project Dashboard

A small read-only dashboard that shows a project's tree, searches it, and displays folder
descriptions. It uses only documented endpoints and never writes.

## What You Will Build

A single page with three panels:

1. A tree of folders, expandable, with descriptions on hover.
2. A search box that calls `POST /api/search`.
3. A result list showing path, summary and relevance.

## Step 1: Fetch the Tree

`GET /api/projects/{id}/directories/{root_id}` returns one level. Walk it recursively:

```ts
type Dir = {
  id: string;
  name: string;
  description: string | null;
  file_count: number;
  directories: { id: string; name: string }[];
};

async function loadTree(rootId: string): Promise<Dir[]> {
  const res = await fetch(`${API}/api/directories/${rootId}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw new Error((await res.json()).error.code);
  const node: Dir = await res.json();
  return node.directories.map((child) => ({ ...child, children: [] }));
}
```

Load children lazily on expand — a 400-node tree in one request makes the first paint slow and
usually unnecessary.

## Step 2: Render Descriptions, Not Just Names

The folder description is the point of the product. Show it beside each name, truncated:

```html
<details>
  <summary>
    <strong>oncall/</strong>
    <span class="desc">Escalation paths and expectations for the on-call engineer.</span>
  </summary>
  <!-- children -->
</details>
```

If `description` is `null` the folder has not been described yet — show "not described" rather
than an empty space.

## Step 3: Search

```ts
async function search(query: string) {
  const res = await fetch(`${API}/api/search`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ project_id: projectId, query, limit: 10 }),
  });
  const data = await res.json();
  return data.results; // [{ path, summary, relevance }]
}
```

Debounce input by 400 ms. Search takes 1.5–4 s on a typical tree; firing per keystroke will hit
the 30/minute limit quickly — see [Rate limits](../api/rate-limits.md).

## Step 4: Show Honest Metadata

Display `folders_visited` and `fallback_used` under the results. When `fallback_used` is true,
say so — it tells the user the query was a poor match rather than that the docs are empty.

```text
9 folders searched · full sweep used · 3.4 s
```

## Step 5: Handle Failures

| Status | What to show |
| :--- | :--- |
| 429 | "Slow down — try again in {Retry-After}s" |
| 401 | Redirect to login |
| 404 | "This project no longer exists" |
| 504 | "Search timed out; try a shorter query" |

Never surface the raw `message`; branch on `code` as described in [Errors](../api/errors.md).

## Step 6: Keep It Read-Only

Use a `viewer` role token. The dashboard cannot import or place documents, so a compromised token
cannot alter a project — see [Access control](../security/access-control.md).

## Where to Take It

- Add keyboard navigation over results; the tree is naturally ordered.
- Cache directory listings in memory for the session and invalidate on `import.completed` from a
  [webhook](../api/endpoints/webhooks.md).
- Show a badge when a project's root description is older than its last import, which usually
  means a failed re-description.
