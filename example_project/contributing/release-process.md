# Release Process

Releases are minor-versioned and cut roughly every two weeks, or immediately for a security fix.
There is no release branch; the tag is the release.

## Cadence

| Type | When | Approval |
| :--- | :--- | :--- |
| Patch (`1.8.x`) | Any fix needed in production, as required | One reviewer |
| Minor (`1.x.0`) | Every two weeks, from `main` | Two reviewers |
| Major (`2.0.0`) | Only with a written migration plan | Team decision |

## Versioning Rules

- **Patch:** bug fixes, prompt tweaks that do not change output shape, dependency bumps.
- **Minor:** new endpoints, new configuration, new tables, response additions.
- **Major:** removing a field, changing an error code, or anything that needs a customer action.

Adding a field is minor. Changing its meaning is major.

## Cutting a Release

1. Confirm `main` is green and the changelog entry for the version is complete.
2. Bump the version in the root `package.json` and any package that pins it.
3. `git tag -a v1.8.2 -m "1.8.2"` then `git push origin v1.8.2`.
4. CI builds, runs integration tests, and deploys to staging automatically.
5. Run the smoke test from [Deployment](../guides/deployment.md).
6. Approve the production gate; the deploy applies migrations on boot.
7. Watch the overview dashboard for ten minutes.

## Changelog Rules

Every user-visible change gets one line in `changelog/YYYY-MM.md`, grouped under *Added*,
*Changed*, *Fixed* or *Deprecated*. Write it for a user, not for a reviewer:

```text
- Search now falls back to a full sweep on projects with 40 or fewer documents.
```

## Migration Discipline

Migrations are forward-only and applied automatically. Therefore:

- Every minor must be schema-compatible with the previous minor.
- Destructive changes land in two releases: stop reading, then drop the column.
- A migration that cannot complete inside 30 seconds needs a maintenance window.

## Hotfixes

Branch from the tag, not from `main`, apply the smallest possible change, cut a patch, and
cherry-pick the fix back to `main`. A hotfix that drifts from `main` becomes tomorrow's outage.

## Related
- [Deployment](../guides/deployment.md)
- [Review checklist](./review-checklist.md)
- [Changelog](../changelog/2026-11.md)
