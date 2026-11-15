# Workstreams

Status: Agreed · Owner: Priya Raman · Last updated: 2026-11-06

Seven workstreams, each with one lead who owns the answer rather than the activity. The folder
column points at where that workstream's documentation lives.

| ID | Workstream | Lead | Scope in one sentence | Folder |
| :--- | :--- | :--- | :--- | :--- |
| WS1 | Current state | Dan Whitcombe | How orders reach warehouses today, and where it breaks | [current-state](../../current-state/) |
| WS2 | Reservation policy | Sofia Mendes | When stock is reserved, held and released | [reservation-policy](../../reservation-policy/) |
| WS3 | Stock feeds | Dan Whitcombe | Warehouse and store stock reaching the platform accurately and fast | [stock-feeds](../../stock-feeds/) |
| WS4 | Delivery promise | Gavin Shore | Turning stock and carrier capacity into a date the customer sees | [delivery-promise](../../delivery-promise/) |
| WS5 | Customer testing | Aisha Bello | Proving it works, with our own teams and with real customers | [customer-testing](../../customer-testing/) |
| WS6 | Launch and operations | Marcus Feld | Cutover, rollback, hypercare and steady-state support | [launch-readiness](../../launch-readiness/) |
| WS7 | Platform and architecture | Nadia Kerr | The services, data model, SLOs and environments underneath WS1–WS6 | [architecture](../../architecture/) |

## How the workstreams interlock

WS1 is finished and gates nothing further, but every later document cites it. WS2 decides the rules
that WS7 implements, so a policy change after 2027-01-11 costs build time. WS3 supplies the numbers
WS4 turns into dates; if feed latency misses its budget, the delivery promise has to become more
conservative. WS5 tests WS2 and WS4 together, because most realistic failures are a policy and a
promise disagreeing. WS6 owns the go-live sequence and inherits WS5's exit criteria.

## Workstream rhythms

Each lead runs a weekly 45-minute review with the programme office and publishes notes into their
own folder within two working days. Notes are deliberately kept next to the work they describe
(for example the reservation workshop note lives in `reservation-policy/specification/`), which
keeps the tree navigable and stops the programme folder becoming a dumping ground.

## Decisions that cut across workstreams

Three subjects appear in more than one workstream and are therefore owned centrally:

- **Standard vocabulary** — [glossary](../../reference/glossary.md), owned by Tom Alder.
- **Data protection** — anything holding a postcode or address, owned by Leah Okafor.
- **Error taxonomy** — [error codes](../../reference/api/error-codes.md), owned by Nadia Kerr.

## Related

[Milestones](./milestones.md) · [Resourcing](./resourcing.md) ·
[Dependencies](./dependencies.md)
