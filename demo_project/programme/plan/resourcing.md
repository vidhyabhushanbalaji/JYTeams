# Resourcing

Status: Agreed · Owner: Priya Raman · Last updated: 2026-11-06

Who is on the programme, how much of their time it takes, and where the gaps are. Allocation is
the percentage of a working week, averaged across the build window.

## Core team

| Role | Name | Allocation | Workstream |
| :--- | :--- | :--- | :--- |
| Programme lead | Priya Raman | 100 % | Programme office |
| Product owner, digital | Tom Alder | 60 % | WS4, WS5 |
| Head of fulfilment | Sofia Mendes | 40 % | WS2 |
| Integration lead | Dan Whitcombe | 100 % | WS1, WS3 |
| QA lead | Aisha Bello | 80 % | WS5 |
| Platform engineering lead | Nadia Kerr | 80 % | WS7 |
| Carrier and transport manager | Gavin Shore | 30 % | WS4 |
| Customer operations manager | Marcus Feld | 40 % | WS6 |
| Change and comms manager | Jo Bell | 50 % | WS6 |
| Data protection officer | Leah Okafor | 10 % | Cross-cutting |
| Finance systems lead | Ben Osei | 20 % | WS3, launch |

## External

| Supplier | People | Why |
| :--- | :--- | :--- |
| Cortex Partners | 2 integration engineers, 1 Kafka specialist | Build capacity and event-platform skills we do not have in-house |
| StockFlow (Northgate Fulfilment) | 1 WMS engineer, 0.5 analyst | Feed contract and mapping |
| LogiCore (Riverside Logistics) | 1 WMS engineer | Bulky stock feed |
| Parcelway | Solutions architect | Delivery promise API integration |

## Budget

Approved envelope is £1.41 m: £620 k internal effort, £470 k Cortex Partners, £180 k licences
(Kafka, Redis, observability), £95 k carrier and 3PL change requests, £45 k contingency. Spend at
2026-11-13 is 22 % of envelope, which is on profile.

## Single points of failure

| Person | Risk | Mitigation |
| :--- | :--- | :--- |
| Dan Whitcombe | Knows all five warehouse feeds and the Orbit mappings | Pairing with a Cortex engineer from January; feed contracts written down in `stock-feeds/protocol/` |
| Nadia Kerr | Only person who can release the platform | Release process documented with Ben Osei as secondary |
| Sofia Mendes | Sole business owner of reservation policy | Tom Alder named deputy; policy rules written to be read without her |

## Skills gaps

Event-stream operations, exactly-once reconciliation against a batch ledger, and carrier API
integration. The first two are covered by Cortex Partners; the third is being learned by Gavin's
team with Parcelway's architect.

## Related

[Workstreams](./workstreams.md) · [Milestones](./milestones.md)
