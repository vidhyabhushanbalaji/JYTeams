# Code Style

We use TypeScript across the monorepo and Prettier plus ESLint to settle arguments. Everything
below is enforced by tooling unless marked *convention*.

## Formatting

```bash
pnpm format        # prettier --write
pnpm lint --fix    # eslint --fix
```

| Rule | Value |
| :--- | :--- |
| Indent | 2 spaces |
| Quotes | double, except in JSON |
| Semicolons | always |
| Max line | 100 characters |
| Trailing commas | always in multiline |

## Naming

| Kind | Convention | Example |
| :--- | :--- | :--- |
| Files | `kebab-case` | `import-job.ts` |
| Types, classes | `PascalCase` | `DirectoryNode` |
| Functions, variables | `camelCase` | `describeDirectory` |
| Constants | `SCREAMING_SNAKE_CASE` | `MAX_UPLOAD_BYTES` |
| Database columns | `snake_case` | `content_hash` |
| HTTP paths | `kebab-case` | `/api/add-requests` |

## Module Boundaries

- `packages/shared` must not import from `apps/`.
- `apps/api` must not import from `apps/web`.
- A service module may import its own repository, never another service's.
- Anything crossing a boundary needs a typed contract in `packages/shared`.

> If you need two services to share logic, extract it into `packages/shared` rather than
> importing sideways.

## Error Handling

Throw domain errors, not strings:

```ts
throw new MeridianError("PROJECT_NOT_FOUND", { projectId });
```

The HTTP layer maps codes to statuses; handlers never construct a status code by hand. Retryable
versus not is a property of the code, defined once in `packages/shared/errors.ts`.

## Async Rules

- No floating promises — ESLint fails on an unawaited promise.
- Prefer `Promise.all` over sequential awaits when calls are independent.
- Never `await` inside a loop over model calls without a concurrency limiter.

## Comments

Comment the *why*. A comment restating the code will be deleted in review.

```ts
// The model's relevance scores are per-call, so all candidates must be
// ranked in a single call to be comparable.
```

## Tests

Test files sit next to the code as `*.test.ts`; integration tests live in `test/integration`.
Names read as sentences: `it("prunes empty directories").`

## Convention, Not Enforced

- Prefer early returns to nested conditionals.
- Keep functions under about 40 lines.
- One exported function per file where practical.
