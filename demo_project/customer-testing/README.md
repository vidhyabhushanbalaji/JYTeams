# Customer Testing

Status: In review · Owner: Aisha Bello · Last updated: 2026-11-13

Proving the platform works, first with our own teams and then with real customers. The name is
deliberate: the purpose of testing here is not to find software defects but to find the moments where
a correct system still produces a wrong experience for a customer.

## The phases

| Phase | When | Who | What it proves |
| :--- | :--- | :--- | :--- |
| Automated regression | Continuous from January | Engineering | The rules stay implemented |
| Integration testing | Feb–Mar 2027 | Engineering, Dan | Feeds, carriers, orders |
| System testing | Mar–Apr 2027 | Aisha's team | End-to-end behaviour |
| UAT | 6–30 April 2027 | Business teams | It does what the business needs |
| Beta | 12–26 April 2027 | 400 customers | It works for real people |
| Hypercare validation | 18 May onwards | Operations | It works at scale, live |

## What "customer testing" means here

Two audiences, deliberately separated:

- **UAT** is our own people acting as customers, with test scripts and known data. It is good at
  finding gaps between the policy and the build.
- **Beta** is 400 real customers on the website only, with real orders and real money, supported by a
  named team. It is good at finding everything else.

Beta runs **alongside** UAT, not after it, because the calendar does not allow a sequential month.
That overlap is a risk and is planned for in the beta cohort document.

## Where to read

| Question | Document |
| :--- | :--- |
| How is testing organised? | [Test strategy](./strategy/test-strategy.md) |
| What must be true to pass? | [Acceptance criteria](./strategy/acceptance-criteria.md) |
| Where does it run? | [Environments](./strategy/environments.md) |
| What data is used? | [Test data](./strategy/test-data.md) |
| What exactly do we test? | [Test cases](./test-cases/) |
| Who are the beta customers? | [Beta cohort](./beta/beta-cohort.md) |
| What did beta tell us? | [Week 1](./beta/beta-report-week-1.md) · [Week 2](./beta/beta-report-week-2.md) |
| How does UAT sign off? | [UAT plan](./uat/uat-plan.md) · [Exit criteria](./uat/entry-and-exit-criteria.md) |
| Non-functional testing | [Performance](./non-functional/performance-testing.md) · [Security](./non-functional/security-testing.md) |

## Current status

| Item | Status | Note |
| :--- | :--- | :--- |
| Test strategy | Agreed | Signed off 2026-11-13 |
| Acceptance criteria | Draft v0.9 | 22 criteria, 18 measurable, 4 pending policy |
| UAT environment | Not built | Build starts 2027-03-01 |
| Beta recruitment | Planned | 400 customers, website only |
| DPIA | Draft | Needed before recruitment (DEP-04) |
| Defect process | Agreed | Severity definitions in UAT folder |

## The rule that governs everything

No test passes on the basis that "the code looks right". Every acceptance criterion has a number and
a measurement window, and anything that cannot be measured is rewritten until it can. Four criteria
are currently in that state because they depend on RSV-06 and RSV-11 being decided.

## Related

[Programme milestones](../programme/plan/milestones.md) · [Reservation rules](../reservation-policy/policy/reservation-rules.md) ·
[Go/no-go checklist](../launch-readiness/cutover/go-no-go-checklist.md)
