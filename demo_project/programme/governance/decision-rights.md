# Decision Rights

Status: Agreed · Owner: Priya Raman · Last updated: 2026-11-06

Who decides what, so that a decision does not wait for a meeting it does not need. "Decides" means
the person whose answer stands; "consulted" means they must be asked before the decision is
recorded.

## The table

| Decision | Decides | Consulted | Recorded in |
| :--- | :--- | :--- | :--- |
| A reservation rule | Sofia Mendes | Tom Alder, Nadia Kerr | [Policy configuration](../../reservation-policy/specification/policy-configuration.md) |
| Reservation expiry windows | Sofia Mendes | Tom Alder | Rule table RSV |
| Architecture and service boundaries | Nadia Kerr | Dan Whitcombe, Iain McCrae | [ADR](../../decisions/) |
| A new carrier or service level | Gavin Shore | Ruth Iyer, Tom Alder | [Carrier onboarding](../../delivery-promise/carriers/carrier-onboarding.md) |
| Feed format for a warehouse | Dan Whitcombe | Nadia Kerr, warehouse owner | [Feed contracts](../../stock-feeds/protocol/feed-contracts.md) |
| Customer-facing wording | Tom Alder | Jo Bell, Leah Okafor | [Customer messaging](../../delivery-promise/customer-messaging/) |
| Beta cohort size and profile | Aisha Bello | Tom Alder, Marcus Feld | [Beta cohort](../../customer-testing/beta/beta-cohort.md) |
| Defect severity | Aisha Bello | Workstream lead | [Defect triage](../../customer-testing/uat/defect-triage.md) |
| Go/no-go | Steering group | All leads | [Checklist](../../launch-readiness/cutover/go-no-go-checklist.md) |
| Rollback during launch | Marcus Feld | Priya Raman, Nadia Kerr | [Rollback triggers](../../launch-readiness/rollback/rollback-triggers.md) |
| Budget above £25 k | Steering group | Finance | Steering minutes |
| Change above 15 days of effort | Steering group | Affected leads | [Change control](./change-control.md) |

## Not delegated

Three things are reserved to the steering group whatever their size: moving a milestone date,
launching or pausing a channel, and accepting a customer-facing promise we know to be wrong.

## Deciding when the owner is away

The named deputy decides: Tom Alder for policy, Dan Whitcombe for architecture, Jo Bell for
customer wording. A deputy decision is provisional until the owner confirms it in writing, and the
confirmation goes into the same document the decision touches.

## Disagreement

If two leads disagree, the programme lead frames the options and the sponsor chooses within five
working days. The disagreement and the resolution both go into the risk register, because an
unresolved disagreement is a risk even when the decision is made.

## Related

[Steering group](./steering-group.md) · [Change control](./change-control.md) ·
[Risk register](./risk-register.md)
