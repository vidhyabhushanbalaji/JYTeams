# Pull Requests

A pull request should be cheap to review. That means small, focused, and explained.

## Before Opening

```bash
pnpm lint && pnpm test
git fetch origin && git rebase origin/main
```

Rebase rather than merge so history stays linear. Fix up your own commits before requesting
review — reviewers read commits, not just the diff.

## Branch Names

```text
feat/incremental-reimport
fix/job-lease-expiry
docs/placement-tutorial
chore/bump-fastify
```

## PR Size

| Size | Lines changed | Review expectation |
| :--- | :--- | :--- |
| Small | < 200 | Review within one working day |
| Medium | 200–500 | Review within two days, one reviewer may ask for a walkthrough |
| Large | > 500 | Explain why; consider splitting into a stacked PR |

A large PR to delete a large amount of code is fine. A large PR that adds a feature, refactors,
and reformats is not.

## Description Template

```markdown
## What changed
Rebuilds the folder description for affected ancestors after a placement.

## Why
Folder descriptions went stale after an add, so search results referred to old names.

## How to review
Start at packages/summariser/redescribe.ts, then the handler.

## Testing
- Added integration test for ancestor propagation
- Manually imported fixtures/handbook and added a file to operations/
```

## Review Etiquette

**Author:** respond to every comment, even if it is "done in abc1234". Mark a conversation
resolved only when the reviewer would agree.

**Reviewer:** distinguish blocking from optional with `nit:` or `optional:`. If you would merge
it yourself, approve rather than comment.

## Merging

- Squash merge; the PR title becomes the commit subject and must be a valid changelog line.
- At least one approval, plus a second for anything touching migrations, auth or prompts.
- Green checks only. Do not merge past a flaky test — fix or quarantine it.

## After Merging

Delete the branch. If the change is user-visible, add a line to the current
[changelog](../changelog/2026-11.md).

## Related
- [Review checklist](./review-checklist.md)
- [Code style](./code-style.md)
