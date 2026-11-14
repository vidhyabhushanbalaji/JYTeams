# Onboarding

Welcome aboard. This page gets a new engineer from a fresh laptop to a merged pull request in
about half a day.

## Day One Checklist

| Step | Where | Done |
| :--- | :--- | :--- |
| Get repository access | Your team lead | ☐ |
| Install prerequisites | [Installation](../getting-started/installation.md) | ☐ |
| Run the stack locally | [Local development](./local-development.md) | ☐ |
| Run the test suite once | [Testing](./testing.md) | ☐ |
| Read the architecture overview | [Overview](../architecture/overview.md) | ☐ |
| Pick a `good-first-issue` | Issue tracker | ☐ |

## What to Read, in Order

1. [Architecture overview](../architecture/overview.md) — the shape of the system in one page.
2. [Data model](../architecture/data-model.md) — five tables, five invariants.
3. [Code style](../contributing/code-style.md) — habits that will not surprise reviewers.
4. [Decision records](../decisions/0001-use-postgres-ltree.md) — why the tree is an `ltree`.

Skip the rest of the docs until you need them; the [glossary](../reference/glossary.md) is the
best place to look up a word.

## Access You Should Have

- GitHub write access to `example/meridian`
- Read access to the staging Postgres (read-only role)
- Membership of `#meridian-dev` and `#meridian-oncall`
- A model API key for local work — request through the platform team, never share

## Your First Change

Pick something small and real: a typo in the docs, a better error message, a missing test. The
goal is the loop, not the code. Open the pull request early as a draft and ask for a review
when the checks are green.

## Conventions in Two Sentences

Work in small branches named `type/short-description`, and keep each pull request to one
reviewable idea. If a change touches more than one service, explain the sequencing in the
description — see [Pull requests](../contributing/pull-requests.md).

## Who to Ask

| Topic | Channel | Owner |
| :--- | :--- | :--- |
| Local setup, tooling | `#meridian-dev` | Platform team |
| Incidents, alerts | `#meridian-oncall` | On-call rotation |
| Model prompts, summaries | `#meridian-ai` | Search & indexing team |
| Security questions | `#security-help` | Security team |
