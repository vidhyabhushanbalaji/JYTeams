# Tutorial: Placing a New Document

You have a draft runbook and a tree you did not write. This tutorial walks the placement flow,
including how to overrule a suggestion and create a new folder.

## The Draft

`draft/alert-runbook.md` — 400 words, opening with:

> How to react when the p95 latency alert fires, including when to page the platform team and
> when to wait for the deploy to finish rolling out.

The opening paragraph is what the placement walk reasons about, so it should describe the
document's actual subject.

## 1. Ask for Suggestions

```bash
meridian add ./draft/alert-runbook.md --project handbook
```

```text
Suggestions for "alert-runbook.md"

1. oncall/                  0.91
   Escalation paths and expectations for the on-call engineer.
   → The draft describes reacting to an alert, which matches on-call practice.

2. oncall/runbooks/         0.83
   Step-by-step recovery procedures, one file per alert.
   → Existing runbooks for specific alerts live here.

3. (project root)           0.34
   Overview of the handbook and how to navigate it.

Choose 1-3, or 'n' to create a new folder:
```

Three candidates is normal. The project root is always offered so placement never dead-ends.

## 2. Understand the Ranking

Each candidate was reached by a walk that opened only folders whose descriptions aligned with
the draft. The reasons come from a single consolidation call, which is why the scores are
comparable to each other but not to scores from a previous run.

## 3. Choose a Folder

Entering `2` places the file in `oncall/runbooks/`, which already exists:

```text
Placing alert-runbook.md in oncall/runbooks/
  wrote file                     fil_8a13
  re-described oncall/runbooks   (3 files)
  re-described oncall/           (2 folders, 1 file)
  re-described root              (4 folders)
done
```

The ancestors were re-described because their descriptions would otherwise be stale — the
invariant from [Data model](../architecture/data-model.md).

## 4. Create a New Folder Instead

To create a folder at the chosen point, answer `n` and give a name:

```bash
meridian add ./draft/alert-runbook.md --project handbook --new-folder incident-drills
```

`--new-folder` always creates the directory under the highest-ranked candidate. Use `--folder`
to pin the location explicitly.

## 5. Commit via the API

The same flow over HTTP, which is useful in automation:

```bash
curl -X POST http://localhost:8080/api/add-requests \
  -H "Authorization: Bearer $MERIDIAN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"project_id":"prj_91c2","content":"# Alert runbook\n\nHow to react…"}'

curl -X POST http://localhost:8080/api/add-requests/add_2c91/commit \
  -H "Authorization: Bearer $MERIDIAN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"directory_id":"dir_44a1","name":"alert-runbook.md"}'
```

A suggestion is single use and expires after 24 hours. Reusing one returns
`409 ADD_REQUEST_CONSUMED`; using an expired one returns `410 ADD_REQUEST_EXPIRED`.

## When Suggestions Disappoint

| Symptom | Fix |
| :--- | :--- |
| Only the root offered | Add more content to the draft; summaries under 100 characters give the walk nothing |
| Right folder at position 4 | Fine — placement is a suggestion, not a decision |
| Two similar folders both offered | Check whether one is stale; `meridian reindex --failed` |

## Next

[Building a project dashboard](./building-a-project-dashboard.md) uses the tree API to render
this structure outside the CLI.
