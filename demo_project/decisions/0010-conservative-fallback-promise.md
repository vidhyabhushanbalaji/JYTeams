# 0010 — Conservative Fallback, Never a Guessed Date

Status: Accepted · Date: 2026-11-06 · Deciders: Tom Alder, Leah Okafor, Gavin Shore

## Context

Sometimes the platform cannot compute a date: feeds are stale, a carrier is down, or a service is
degraded. The site still needs to tell the customer something at checkout, and consumer law requires a
delivery timeframe to be given.

The temptation is to show a best guess, because a date converts better than a range.

## Options

| Option | Conversion | Risk |
| :--- | :--- | :--- |
| A. Best-guess date, labelled as an estimate | Highest | A broken promise if it is wrong |
| B. Range ("3–5 working days"), no date | Lower | Honest, legally sufficient |
| C. No timeframe at all | Lowest | Legally insufficient |
| D. Hide the product until a date exists | — | Withdraws stock that exists |

## Decision

Fall back to a **range**, state that we will confirm within 24 hours, and never show a specific date we
cannot defend. A fallback order counts as **not promised** in the accuracy metric.

## Why not a best guess

The contact centre interview settles it: customers forgive "three to five days" and do not forgive a
broken Thursday. The baseline shows the same thing at scale: 71 % accuracy is bad precisely because we
were making confident promises on bad data. A labelled guess would be the same mistake with better
presentation.

## Consequences

| Easier | Harder |
| :--- | :--- |
| Customer expectation is honest | Conversion is measurably lower in the fallback state |
| Accuracy metric cannot be flattered | Fallback share becomes a number to manage |
| Legal position is clear | Copy needs review (DEP-08) |
| A degraded platform is visible to the business | Support needs a script for "why no date" |

## The metric rule

A fallback order is recorded with `fallback_used=true` and is excluded from the numerator of promise
accuracy, not counted as a miss. Counting it as a miss would encourage guessing; excluding it silently
would hide the problem, which is why the fallback share is reported next to accuracy on every dashboard.

## What would change this

If fallback share stays above 5 % after the feeds stabilise, the answer is to fix the feeds, not to start
guessing. That is the one interpretation of this record that the team has agreed will not be revisited.

## Related

[Fallback messaging](../delivery-promise/customer-messaging/fallback-messaging.md) ·
[Unavailable dates](../delivery-promise/calculation/unavailable-dates.md) ·
[Promise accuracy](../delivery-promise/customer-messaging/promise-accuracy.md)
