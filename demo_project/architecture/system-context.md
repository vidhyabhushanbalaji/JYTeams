# System Context

Status: Draft · Owner: Nadia Kerr · Last updated: 2026-11-06

Who and what the platform sits between. The boundary matters more than the internals: everything
outside it is a dependency with its own failure behaviour.

## Actors

| Actor | Interacts with | Needs |
| :--- | :--- | :--- |
| Customer | Storefront | A date they can trust |
| Contact centre agent | Agent screen | The same date the customer saw |
| Fulfilment team | Admin console | Holds, releases, exceptions |
| Store colleague | Store task list | A pick task that is clear |
| Warehouse supervisor | Warehouse system | Nothing new, ideally |
| Trading | Trading tools | Stock visibility by channel |
| Finance | Horizon | A reconcilable number |

## External systems

| System | Direction | Interface | Owner |
| :--- | :--- | :--- | :--- |
| Shopify | In and out | Webhooks, API | Ruth Iyer |
| Amazon | In and out | SP-API via ChannelBridge | Kelvin Adu |
| eBay | In and out | API via ChannelBridge | Kelvin Adu |
| Mercury | In and out | REST, events | Ben Osei |
| Horizon | Out | Nightly batch | Ben Osei |
| Orbit | In and out | Files, REST | Dan Whitcombe |
| Atlas | In | API | Tom Alder |
| DC-WMS | In | SQL view or API | Sofia Mendes |
| StockFlow | In | REST | Northgate |
| LogiCore | In | REST | Riverside |
| StoreStock | In | SFTP file | Elena Vasquez |
| Parcelway | In and out | REST | Gavin Shore |
| Northline | In and out | REST | Gavin Shore |
| Swiftbox | In and out | REST | Gavin Shore |

## Boundary rules

| Rule | Why |
| :--- | :--- |
| No external system writes to platform data directly | Only the ingestor writes stock; only the worker writes reservations |
| Every external call has a timeout and a fallback | Carrier and marketplace APIs fail; the site must not |
| No synchronous chain longer than two hops | A slow carrier must not slow a product page |
| Every inbound message is authenticated and idempotent | Feed incidents 001 and 004 |
| Outbound calls are rate limited and queued | Marketplace quotas |

## Trust boundaries

| Zone | Contains | Access |
| :--- | :--- | :--- |
| Public | Storefront, marketplace APIs | Internet |
| Platform | ATP, DPS, ingestor, worker | Private network, mTLS |
| Warehouse | DC-WMS, StockFlow, LogiCore | VPN or IP allow-list |
| Finance | Horizon | Separate network |
| Admin | Console, policy configuration | SSO plus MFA |

The admin console is the most dangerous surface in the system: it can hold a warehouse and change a
policy key. It is behind SSO and MFA, every action is audited with a name, and there is no shared
administrator account.

## What we do not integrate with

| Not integrated | Why |
| :--- | :--- |
| Carrier billing | Finance import, not real time |
| Customer identity provider beyond Shopify | Out of scope |
| Store till systems directly | StorePOS is the boundary |
| Supplier systems | Atlas is the boundary |
| Marketing platforms | Different programme |

## Related

[Overview](./overview.md) · [Integration landscape](../current-state/systems/integration-landscape.md) ·
[Security architecture](./platform/security-architecture.md)
