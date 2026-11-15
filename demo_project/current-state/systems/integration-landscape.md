# Integration Landscape

Status: Agreed · Owner: Dan Whitcombe · Last updated: 2026-11-06

The map of who talks to whom today, and the four integration patterns in use. Anything new has to
fit one of these patterns or justify a fifth.

## Today's map

```text
Shopify ──webhook──▶ Orbit ──REST──▶ Mercury ──file──▶ DC-WMS (Midlands, Glasgow)
Amazon/eBay ──poll──▶ ChannelBridge ──REST──▶ Mercury ──delta API──▶ StockFlow (Northgate)
Trade portal ──REST──────────────▶ Mercury ──delta API──▶ LogiCore (Riverside)
StorePOS ──nightly file──▶ Orbit ──batch──▶ Mercury ──nightly file──▶ StoreStock
Mercury ──nightly extract──▶ Horizon
Mercury ──30 min extract──▶ ChannelBridge ──▶ marketplaces
```

## The four patterns

| Pattern | Used for | Latency | Failure behaviour |
| :--- | :--- | :--- | :--- |
| Synchronous REST | Order creation, portal calls | 2–40 s | Caller sees the error |
| Scheduled pull | Marketplace orders, warehouse feeds | 5–15 min | Retried next cycle |
| File drop | EDI, store stock, dispatch notes | 15 min–24 h | Operator re-sends |
| Nightly batch | Ledger, routing, extracts | Hours | Re-run the next night |

## What Orbit is

Orbit is the integration hub: a 2018 MuleSoft installation that owns the mappings, the queues and
the dead-letter directory. It is reliable but opaque. There is no per-message observability, only a
log file on a server that two people can read, and a dead-letter folder that is checked when
somebody remembers.

That opacity is the direct cause of F-04 (stuck orders for six hours) and F-08 (missed marketplace
dispatch confirmations): both failed silently in Orbit and were discovered by customers.

## What Truestock adds

| New path | Pattern | Replaces |
| :--- | :--- | :--- |
| Warehouse feeds → stock feed ingestor | Event stream | Orbit batch pulls |
| Orders → reservation worker | Event stream | Polling Mercury |
| ATP → storefront, marketplaces | Synchronous REST, cached | Mercury extracts |
| DPS → carriers | Synchronous REST | Manual booking |
| Platform → Horizon memorandum | Nightly batch | Nothing (new) |

The event stream is a Kafka cluster (`truestock-events`) managed by Cortex Partners, with one
topic per domain event and a schema registry. Orbit keeps the file and EDI traffic, so the release
removes about 60 % of Orbit's message volume rather than retiring it.

## Rules for new integrations

1. Every message has an idempotency key and a timestamp.
2. Every consumer has a dead-letter path and an alert, not a folder.
3. Every mapping is documented in a contract, not in code only.
4. No new nightly batch may be introduced for anything that affects a promise.

## Related

[Mercury OMS](./mercury-oms.md) · [Event flows](../../architecture/event-flows.md) ·
[Failure and retry](../../stock-feeds/reliability/failure-and-retry.md)
