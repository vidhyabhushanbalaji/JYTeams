# Feedback Survey

Status: Draft · Owner: Tom Alder · Last updated: 2026-11-13

Two short surveys, one on day two and one on day ten, plus a single question in the post-delivery
email. Together they take under four minutes and produce the qualitative half of the beta result.

## Survey 1 — day 2 (after ordering)

| ID | Question | Type |
| :--- | :--- | :--- |
| S1-01 | Did you see a delivery date before you paid? | Yes / no / not sure |
| S1-02 | Was the date what you expected? | 5-point |
| S1-03 | Did you understand how many parcels to expect? | Yes / no / not sure |
| S1-04 | How confident were you that the date would be kept? | 5-point |
| S1-05 | Was anything confusing at checkout? | Free text |

## Survey 2 — day 10 (after delivery)

| ID | Question | Type |
| :--- | :--- | :--- |
| S2-01 | Did your order arrive on the promised day? | Yes / earlier / later / not yet |
| S2-02 | If it changed, were you told before you noticed? | Yes / no / not applicable |
| S2-03 | How would you rate the delivery experience? | 5-point |
| S2-04 | Would you shop with us again based on this? | 5-point |
| S2-05 | What would have made the experience better? | Free text |
| S2-06 | Did you use store collection? | Yes / no |
| S2-07 | (If yes) Was the item ready when we said? | Yes / no |

## Post-delivery email

One question, no login required: "Did your order arrive when we said?" with three options. It gives a
larger sample than the surveys and is the source for the beta accuracy cross-check against carrier
tracking.

## Analysis plan

| Output | Method | Audience |
| :--- | :--- | :--- |
| Stated versus actual accuracy | S2-01 versus tracking | Beta report |
| Confidence score | S1-04 mean, split by segment | Beta report |
| Confusion themes | Free-text coding, two reviewers | Product |
| Parcel expectation | S1-03 versus actual shipping | Messaging review |
| Collection readiness | S2-07 versus store scan | Store operations |

Free-text responses are coded independently by Tom Alder and Marcus Feld, and only themes both
identify are reported as findings. A theme one reviewer sees is a hypothesis, not a result.

## Sample expectations

| Measure | Expected responses | Confidence |
| :--- | :--- | :--- |
| Survey 1 | 230 of 400 (58 %) | ±4 % |
| Survey 2 | 180 of 400 (45 %) | ±5 % |
| Post-delivery email | 350 of 620 orders (56 %) | ±4 % |

The response rates are from the October trial and are optimistic for a two-week window; the analysis
plan works at 40 % too, which is why it is stated rather than hoped for.

## What we will not do

| Temptation | Why not |
| :--- | :--- |
| Ask about price | Not in scope, and it biases the promise questions |
| Ask about the brand | Different research programme |
| Add questions mid-flight | Breaks comparability between weeks |
| Use survey responses as the accuracy metric | Stated accuracy is not measured accuracy |

The fourth point matters: customers often remember a delivery as on time because it was convenient,
while tracking says otherwise. Tracking is the metric; the survey explains the experience.

## Related

[Beta cohort](./beta-cohort.md) · [Beta report week 1](./beta-report-week-1.md) ·
[Promise accuracy](../../delivery-promise/customer-messaging/promise-accuracy.md)
