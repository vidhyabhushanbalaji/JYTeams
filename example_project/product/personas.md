# Personas

Four people use Meridian, and they want different things from it. Design reviews name the
persona affected; a change that helps nobody in this list is usually a mistake.

## 1. Priya — Platform Engineer

**Context:** Owns infrastructure for a 60-person engineering org. Knows where things are *in
principle*, gets paged at 3am when the answer is in a document nobody read.

| Attribute | Detail |
| :--- | :--- |
| Uses | Search, runbooks |
| Frequency | Daily, heavily during incidents |
| Cares about | Speed, accuracy, "does it know what I mean at 3am" |

**Needs:** a query in plain language returns the right runbook, and the summary is trustworthy
enough to act on without opening the file first.

**Frustration:** searching for the symptom rather than the document title returns nothing.

## 2. Tomás — Documentation Maintainer

**Context:** Maintains the handbook. Spends an hour a week filing new pages into the right
folder and fixing links.

| Attribute | Detail |
| :--- | :--- |
| Uses | Add, import, tree view |
| Frequency | Weekly |
| Cares about | Placement quality, folder descriptions staying accurate |

**Needs:** adding a new page suggests the folder a colleague would have chosen, including when
the right answer is "create a new folder here".

**Frustration:** a good suggestion hidden behind three weak ones.

## 3. Aisha — Engineering Manager

**Context:** Wants to know whether documentation matches reality without reading 400 files.

| Attribute | Detail |
| :--- | :--- |
| Uses | Tree view, folder descriptions |
| Frequency | Monthly, plus during onboarding |
| Cares about | Coverage, staleness, where the gaps are |

**Needs:** folder descriptions that summarise rather than list, so a whole area can be assessed
in a minute.

## 4. New Joiner (any name)

**Context:** Day one. Does not know the vocabulary yet, so cannot search for the right words.

| Attribute | Detail |
| :--- | :--- |
| Uses | Quick start, tree browse |
| Frequency | Intense first two weeks |
| Cares about | Not having to ask a human |

**Needs:** browsing that makes the shape of the knowledge obvious, and search that tolerates
vague questions.

**Frustration:** every result assumes context they do not have.

## Anti-Persona

**The automated scraper.** A script that imports thousands of unrelated files and searches
continuously. It is handled by rate limits, not by design work — see
[Rate limits](../api/rate-limits.md).
