# Glossary

Status: Agreed · Owner: Tom Alder · Last updated: 2026-11-13

The words this programme uses, in the sense it uses them. Where a word has a meaning in the wider
business that differs from the platform, the platform's meaning is the one written here.

## A–C

| Term | Meaning | More |
| :--- | :--- | :--- |
| **Allocation** | A warehouse has put a reserved unit on a pick list. Stronger than a reservation, because a picker can reach it. | [Lifecycle](../reservation-policy/policy/reservation-lifecycle.md) |
| **ATP** | Available to promise: the number of units that can be sold now, from a location, net of reservations and quarantine. | [ATP contract](../reservation-policy/specification/atp-service-contract.md) |
| **Backorder** | A line accepted against stock that is not yet available, with a "from" date rather than a promise. | [Pre-orders](../reservation-policy/policy/pre-orders-and-backorders.md) |
| **Bulky** | A product requiring two-person delivery: over 30 kg, or over 1.2 m. Always Riverside and Northline. | [Northline](../delivery-promise/carriers/northline-freight.md) |
| **Carrier serviceability** | Whether a carrier will deliver a given service to a given postcode, and in what lead time. | [Postcode lookup](../delivery-promise/customer-messaging/postcode-lookup.md) |
| **Collection hold** | The five days a picked collection order waits for the customer, after which it is released. | [Store collection](../reservation-policy/edge-cases/store-collection.md) |
| **Cut-off** | The time after which an order is promised the next working day. Two exist: promise cut-off and carrier cut-off. | [Cut-off times](../delivery-promise/calculation/cut-off-times.md) |

## D–L

| Term | Meaning | More |
| :--- | :--- | :--- |
| **Delta** | A feed containing only records changed since a cursor, as opposed to a full snapshot. | [Delta and snapshot](../stock-feeds/protocol/delta-and-snapshot.md) |
| **Degraded** | A state where some data is stale but a date can still be given, with a caveat. | [Stale handling](../stock-feeds/reliability/stale-stock-handling.md) |
| **Fallback** | The estimate shown instead of a date when no defensible date exists. Counts as not promised. | [Fallback messaging](../delivery-promise/customer-messaging/fallback-messaging.md) |
| **Hard allocation** | See allocation. Used to distinguish it from a soft reservation. | [Lifecycle](../reservation-policy/policy/reservation-lifecycle.md) |
| **Hypercare** | The four weeks after launch with a named team, daily checkpoints and stricter escalation. | [Hypercare plan](../launch-readiness/hypercare/hypercare-plan.md) |
| **ISO week** | Used for peak capacity planning only, never for promises. | [Peak calendar](../delivery-promise/calculation/peak-and-holiday-calendar.md) |
| **Locker** | A Swiftbox unattended collection point, 24-hour service, size-limited. | [Swiftbox](../delivery-promise/carriers/swiftbox-lockers.md) |

## M–R

| Term | Meaning | More |
| :--- | :--- | :--- |
| **Mercury** | The order management system: orders, routing, dispatch. Not the stock system of record from launch. | [Mercury](../current-state/systems/mercury-oms.md) |
| **Orbit** | The integration hub owning EDI, file transfers and legacy batch. | [Integration landscape](../current-state/systems/integration-landscape.md) |
| **Oversell** | An order line cancelled because the stock did not exist, code `NO_STOCK_AFTER_ORDER`. | [Oversell prevention](../reservation-policy/policy/oversell-prevention.md) |
| **Phantom stock** | Stock the system believes exists and the shelf does not have. Distinct from oversell, which is its consequence. | [Known failures](../current-state/order-flow/known-failures.md) |
| **Pre-order** | A product sold before release, with a release date rather than a delivery date. | [Pre-orders](../reservation-policy/policy/pre-orders-and-backorders.md) |
| **Promise** | A specific delivery day given to a customer, stored at the moment it was given. | [Promise accuracy](../delivery-promise/customer-messaging/promise-accuracy.md) |
| **Promise accuracy** | Share of orders delivered on the promised day. The programme's headline metric. | [Promise accuracy](../delivery-promise/customer-messaging/promise-accuracy.md) |
| **Quarantine** | Units physically present and not sellable: damage, quality hold, client hold. | [Quarantine](../reservation-policy/edge-cases/damaged-and-quarantine-stock.md) |
| **Release** | Ending a reservation, always with one of eight reason codes. | [Cancellations](../reservation-policy/policy/cancellations-and-releases.md) |
| **Reservation** | A claim on a unit by an order, in `soft`, `allocated` or `dispatched` state. | [Lifecycle](../reservation-policy/policy/reservation-lifecycle.md) |

## S–Z

| Term | Meaning | More |
| :--- | :--- | :--- |
| **Snapshot** | A full feed of every record at a point in time. Self-correcting and expensive. | [Delta and snapshot](../stock-feeds/protocol/delta-and-snapshot.md) |
| **Soft reservation** | A claim held for 30 minutes from payment authorisation, invisible to the warehouse. | [Lifecycle](../reservation-policy/policy/reservation-lifecycle.md) |
| **Split shipment** | One order dispatched in more than one parcel, each with its own promise. | [Split shipments](../reservation-policy/edge-cases/split-shipments.md) |
| **Stale** | A feed older than its threshold, measured on the source timestamp, not arrival time. | [Stale handling](../stock-feeds/reliability/stale-stock-handling.md) |
| **Store task** | The pick instruction sent to a store's handheld or back-office list. | [Store collection](../reservation-policy/edge-cases/store-collection.md) |
| **UAT** | User acceptance testing: business teams, 6–30 April 2027. | [UAT plan](../customer-testing/uat/uat-plan.md) |
| **3PL** | Third-party logistics: Northgate Fulfilment and Riverside Logistics. | [Warehouse systems](../current-state/systems/warehouse-systems.md) |
| **WMS** | Warehouse management system. Four in use, none of them ours. | [Warehouse systems](../current-state/systems/warehouse-systems.md) |

## Words we avoid

| Avoided | Why |
| :--- | :--- |
| "Real-time stock" | We are a five-minute platform on a good day; the claim would be false |
| "Live availability" | Same problem, and customers interpret it as a guarantee |
| "Guaranteed delivery" | No carrier offers one |
| "System error" in customer copy | It invites a call and explains nothing |

## Related

[Architecture](../architecture/README.md) · [Reservation rules](../reservation-policy/policy/reservation-rules.md) ·
[Error codes](./api/error-codes.md)
