# Runbook — ATP Service Outage

**Symptom:** product pages show a fallback date or no date; checkout refuses to quote; availability
latency alerts fire.

**Customer impact:** every new order loses its date. Reservations stop, so stock is not protected. This
is the most serious single-service failure.

## 1. Establish the scope (3 minutes)

| Check | Result | Meaning |
| :--- | :--- | :--- |
| `/health` on ATP | 200 | Service alive, problem downstream |
| Quote latency p95 | > 1 s | Slow, possibly a database or cache issue |
| Error rate | > 5 % | Failing; likely rollback territory |
| Reservation worker | Running? | If stopped, that is your first fix |
| Redis | Up? | Cache miss storm can look like an outage |

## 2. Stabilise (5 minutes)

| Cause | Action |
| :--- | :--- |
| Redis down | Restart Redis; ATP falls back to database reads, expect 900 ms p95 |
| Database connection pool exhausted | Restart ATP pods one at a time, not all |
| Deployment in progress | Stop the rollout, revert to the previous revision |
| Dependency timeout | Check carrier and feed call latency from the ATP dashboard |

Restarting all pods at once causes a cold-cache stampede; one at a time, waiting for health between
each, is slower and safer.

## 3. Decide fallback or rollback (5 minutes)

| Condition | Action |
| :--- | :--- |
| Error rate 5–20 %, reservations working | Serve fallback dates; do not roll back |
| Error rate > 20 % or reservations failing | Soft rollback (see rollback plan) |
| Wrong availability answers observed | Soft rollback immediately |

A fallback date is a degraded experience; a wrong availability answer is a broken promise. Only the
second one is an automatic rollback.

## 4. Communicate (5 minutes)

| Audience | Message |
| :--- | :--- |
| Support | "Dates unavailable for some products; use the order screen date" |
| War room | Incident opened, scope, decision |
| Customers | Banner only if the fallback share exceeds 15 % |

## 5. Recovery checks

- [ ] Quote latency p95 back under 180 ms
- [ ] Reservation success rate above 99 %
- [ ] Fallback share back under 1 %
- [ ] No reservation queue backlog older than 60 seconds
- [ ] Cache warming complete (expect 5 minutes)

## 6. After

1. Raise an incident record with the timeline.
2. Attach the four dashboards for the affected window.
3. If rollback was used, follow the post-rollback steps.
4. Review within five days, owned by Nadia Kerr.

## Escalation

| Time | Who |
| :--- | :--- |
| 0 min | On-call |
| 10 min | Nadia Kerr |
| 15 min | Marcus Feld if customers are affected |
| 30 min | Priya Raman if a rollback is likely |

## Never do

| Never | Why |
| :--- | :--- |
| Increase the cache TTL to "make it faster" | It serves older stock with more confidence |
| Bypass ATP from the storefront | Creates a second availability path |
| Restart the reservation worker while ATP is down | It will retry into a failing service and queue up |
| Announce a fix before the fallback share drops | Customers notice |

## Related

[Rollback plan](../rollback/rollback-plan.md) · [Availability API](../../reference/api/availability-api.md) ·
[Performance targets](../../architecture/platform/performance-targets.md)
