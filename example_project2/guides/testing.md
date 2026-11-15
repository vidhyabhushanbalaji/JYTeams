# Testing

Tests are split by how much they cost to run. Unit tests are always offline; anything that calls
the model uses the stub unless you explicitly ask for a live run.

## Commands

```bash
pnpm test              # unit tests, no network
pnpm test:integration  # Postgres + MinIO via testcontainers
pnpm test:e2e          # full stack, stub model
pnpm test:live         # real model calls, opt-in, costs money
```

## Test Pyramid

| Layer | Count (approx.) | Runtime | Network |
| :--- | :--- | :--- | :--- |
| Unit | 420 | 8 s | none |
| Integration | 60 | 90 s | local containers |
| End-to-end | 12 | 4 min | local stack |
| Live model | 5 | 3 min | external |

## The Model Stub

`@meridian/testing` exposes a scriptable stub:

```ts
import { stubModel } from "@meridian/testing";

const model = stubModel({
  summaries: { "operations/runbooks": "Recovery procedures." },
  fallback: (path) => `Stub summary for ${path}`,
});
```

The stub records every prompt it receives, so prompt tests assert on structure rather than prose:

```ts
expect(model.calls[0].prompt).toContain("folder description");
expect(model.calls).toHaveLength(4);
```

## Writing a Tree Fixture

Build trees in code rather than checking in archives:

```ts
const tree = fixtureTree({
  "README.md": "# Handbook",
  "operations/runbooks/failover.md": "# Failover",
});
await importProject(tree);
```

## What to Test

- **Invariants** from the [data model](../architecture/data-model.md) — one parent, correct counts.
- **Idempotency** — importing the same archive twice creates no duplicate nodes.
- **Failure handling** — a model timeout marks one node `failed` and leaves the tree readable.
- **Pagination and cursor stability** — a page boundary should not skip a row.
- **Error codes** — assert on `code`, not message text.

## What Not to Test

- Exact wording produced by the model in unit tests; that belongs in `test:live`.
- Internal helper functions that are not exported — if it matters, test it through the API.

## Coverage

CI enforces 80% line coverage on `packages/summariser` and 70% elsewhere. Coverage is a floor,
not a target; a well-tested invariant beats a covered getter.
