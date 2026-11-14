# Threat Model

Meridian holds documentation that is often more sensitive than the code it describes. This
model lists what we defend against and what we have explicitly accepted.

## Assets

| Asset | Sensitivity | Where it lives |
| :--- | :--- | :--- |
| Document bodies | High | Object store |
| Summaries and descriptions | High | Postgres |
| Tenant and user identity | Medium | Postgres, token issuer |
| Model API keys | Critical | Secret manager |
| Webhook signing secrets | High | Secret manager, tenant admin |

## Trust Boundaries

1. **Ingress → API.** Untrusted input: paths, archives, query strings.
2. **API → Postgres / object store.** Trusted network, least-privilege credentials.
3. **Worker → model API.** Trusted egress, but prompts contain document text.
4. **Meridian → tenant webhook endpoint.** Data leaves our boundary, signed.

## Threats and Mitigations

| Threat | Mitigation |
| :--- | :--- |
| Path traversal in archive entries | Normalise and reject any path escaping the upload root |
| Zip bomb | Size and entry-count limits, streamed extraction, abort on ratio threshold |
| Prompt injection inside a document | Summaries are treated as data; prompts never grant tool access |
| Cross-tenant data access | Every query filtered by `tenant_id` from token context, not request body |
| Stolen service token | Short TTL, single-project scope, rotation on suspicion |
| Webhook spoofing | HMAC signature over timestamp plus raw body, five-minute window |
| Oversized upload exhausting memory | `MERIDIAN_MAX_UPLOAD_BYTES`, streamed to disk first |

## Prompt Injection

A document can contain text like "ignore previous instructions". Mitigations:

- The model never has tools, only a text-in/text-out contract.
- Prompts place document text inside delimited data blocks and instruct the model to summarise,
  not to obey.
- Output is schema-validated; a summary that does not match the expected shape is discarded and
  the node is marked `failed`.

## Accepted Risks

| Risk | Why accepted | Revisit when |
| :--- | :--- | :--- |
| Summaries reveal sensitive content to the model provider | Required for the core feature | A self-hosted model is viable |
| No folder-level permissions | Tenancy is the only isolation unit in `1.x` | Enterprise onboarding demands it |
| Search cannot verify answers against bodies | Read-only by design | Retrieval grounding is added |

## Out of Scope

Physical security of the hosting provider, supply-chain compromise of the model provider, and
tenant users sharing credentials with each other.

## Review

Revisit every quarter, and whenever a new data category (images, PDFs) enters the product. The
multimodal work in the [roadmap](../product/roadmap.md) is the next trigger.
