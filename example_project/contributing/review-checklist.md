# Review Checklist

Copy this into the PR description for anything non-trivial. It is a prompt, not a gate — delete
lines that genuinely do not apply and say why.

## Correctness

- [ ] The change does what the description says, and nothing else
- [ ] Tree invariants still hold — one parent per directory, accurate `file_count`
- [ ] Repeated runs are idempotent: import twice, no duplicate nodes
- [ ] Failure paths leave a readable tree, not a half-written one
- [ ] Error codes are reused, not invented per handler

## Data and Schema

- [ ] Migration is forward-only with the next sequential number
- [ ] New queries filter by `tenant_id`
- [ ] Indexes exist for any new access pattern
- [ ] Compatible with the previous minor, so rollback is safe

## Model and Prompts

- [ ] Prompt changes have a before/after example in the description
- [ ] Output is schema-validated; invalid output fails the node, not the job
- [ ] No document text is interpolated outside the delimited data block
- [ ] Cost impact estimated (calls per import, per placement, per search)

## Security

- [ ] No secrets, tokens or customer paths in code, fixtures or logs
- [ ] User input reaching SQL is parameterised
- [ ] Archive and path handling rejects escapes and implements size limits
- [ ] New endpoints have an explicit role requirement

## Tests

- [ ] A test fails without this change
- [ ] Unit tests use the model stub, not the network
- [ ] Integration test covers the database behaviour that unit tests cannot
- [ ] No test depends on wall-clock ordering

## Operations

- [ ] New failure mode has a log line with `request_id` or `job_id`
- [ ] New alert or metric documented in [Monitoring](../operations/monitoring.md)
- [ ] Runbook updated if the recovery steps change
- [ ] Rollback path stated in the description

## Documentation

- [ ] User-facing behaviour change reflected in the relevant page
- [ ] Changelog line added for this month
- [ ] Decision record written if this settles a debate future readers will repeat

## Reviewer Sanity

- [ ] I would be comfortable being paged for this change
- [ ] The PR title reads as a changelog line
- [ ] Diff contains no unrelated reformatting
