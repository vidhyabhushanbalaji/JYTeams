# Test Data

Status: Agreed · Owner: Aisha Bello · Last updated: 2026-11-13

What data the tests run against, where it came from, and what must never appear in a test
environment. Getting this wrong either makes tests unrealistic or makes a privacy incident.

## Data sets

| Set | Contents | Rows | Used by |
| :--- | :--- | :--- | :--- |
| Order history | Masked October 2026 orders | 412,000 | UAT, staging |
| Stock fixtures | Five warehouse batches | 556,000 | Integration, UAT |
| Store file | 41,000 store/SKU lines | 41,000 | UAT |
| Product catalogue | Atlas extract, 31,400 sellable SKUs | 31,400 | All |
| Postcode set | 200 postcodes, including 12 edge cases | 200 | Checkout tests |
| Carrier responses | Recorded sandbox responses | 4,800 | Integration |
| Synthetic peak | Generated orders at 3.7× baseline | 52,000/day | Load tests |

## Masking

| Field | Treatment | Why |
| :--- | :--- | :--- |
| Name | Replaced with a consistent fake | Contact tests need a name |
| Address line | Replaced, postcode retained | Postcode drives the promise |
| Email | `customer+{id}@example.test` | Cannot receive mail |
| Phone | Dropped | Never needed in tests |
| Payment | Token only, no card data | Out of scope, never stored |
| Order ID | Retained | Traceability to real behaviour |

Postcodes are retained because serviceability is the whole point of the test. That decision means the
masked set is still personal data at a postcode level, which is why it lives in a restricted
environment and is covered by the DPIA.

## Synthetic data rules

| Rule | Reason |
| :--- | :--- |
| SKUs must exist in Atlas | A test with a fake SKU hides mapping failures |
| Warehouse locations must be the five real ones | Feed logic branches on source |
| Quantities must be plausible (1–500) | Zero and 999,999 hide arithmetic bugs |
| At least 12 % of baskets must be multi-line | Split shipments are the common case |
| At least 3 % must contain a bulky item | The hardest segment |
| Orders must span the day, not just 10:00 | Cut-off bugs hide behind a flat profile |

The last rule is the one that catches cut-off errors, and it is why the synthetic peak generator
distributes orders by the real hourly curve rather than uniformly.

## Prohibited data

| Prohibited | Why |
| :--- | :--- |
| Live customer addresses | Not needed, high risk |
| Card numbers, even test ones | Creates a habit |
| Real supplier pricing | Commercially sensitive |
| Employee names in order data | Unnecessary personal data |
| Production credentials | Obvious, and has happened elsewhere |

## Where the data lives

| Set | Location | Retention |
| :--- | :--- | :--- |
| Masked order history | UAT and staging databases | Deleted after M9 |
| Replay fixtures | Test storage bucket | Deleted after M9 |
| Carrier responses | Test storage bucket, scrubbed | Retained for regression |
| Synthetic peak | Generated per run | Not stored |

Everything created for testing is deleted after hypercare, which is a commitment in the DPIA rather
than an intention.

## Related

[Environments](./environments.md) · [Feed simulator](../../stock-feeds/protocol/feed-simulator.md) ·
[Load profile](../non-functional/load-profile.md)
