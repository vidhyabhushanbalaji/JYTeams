# Reference

Status: Agreed · Owner: Tom Alder · Last updated: 2026-11-13

Look-up material rather than narrative: the words, the fields and the endpoints. If you are reading
reference, you already know what you are trying to do and need the exact spelling of it.

## What is here

| Section | Contains | Use it when |
| :--- | :--- | :--- |
| [Glossary](./glossary.md) | Every programme term, in the sense we use it | Someone says "allocation" and you want to be sure |
| [Data dictionary](./data-dictionary/) | Field-by-field definitions with types and constraints | You are reading a feed, a reservation or a promise |
| [API reference](./api/) | Endpoints, payloads and error codes | You are integrating or debugging |

## The three data dictionaries

| Record | Describes | Written by |
| :--- | :--- | :--- |
| [Stock record](./data-dictionary/stock-record.md) | One SKU at one location | Feed ingestor |
| [Reservation record](./data-dictionary/reservation-record.md) | One claim by one order line | Reservation worker |
| [Promise record](./data-dictionary/promise-record.md) | One date given to one shipment | Delivery promise service |

These three records are the platform's contract with the rest of the business. Everything else in
`architecture/` explains how they are produced; these explain what they mean.

## The error codes

[Error codes](./api/error-codes.md) is the single list of codes the platform returns, with what each
caller should do. It is the most-used document during a launch incident, after the runbooks.

## What is deliberately not here

| Not here | Where |
| :--- | :--- |
| Business rules | [Reservation policy](../reservation-policy/policy/reservation-rules.md) |
| Calculations and worked examples | [Delivery promise](../delivery-promise/calculation/delivery-date-logic.md) |
| Operational procedures | [Runbooks](../launch-readiness/runbooks/runbook-index.md) |
| Explanations of why | [Decisions](../decisions/) |

Reference is kept free of reasoning on purpose. A definition that argues its case is harder to look up,
and the arguments already have a home in the decision records.

## Keeping it accurate

Reference drifts first and is noticed last. Two rules protect it: a field is added here before it is
used in a feed contract, and an error code that appears in a log but not in the list is raised as a
defect rather than quietly documented later.

## Related

[Architecture](../architecture/README.md) · [Glossary](./glossary.md) ·
[Latest status](../programme/status/2026-11-13-status.md)
