# AI Model Usage — Gemini only, 5 requests when the AI tests

## One provider, one model

Every model call in this project goes to Gemini **`gemini-3.1-flash-lite`**, through
`google-genai` and the two describers (`backend/app/graph_creation/describe.py`,
`backend/app/graph_add/describer.py`), configured by `GEMINI_MODEL` in
`backend/app/core/config.py`.

- Groq was retired after repeated API-limit problems. Do not add it back, do not add a second
  provider, and do not reintroduce an `auto` mode that could pick one — if a task seems to
  need another provider, ask first.
- `GEMINI_FALLBACK_MODELS` is **empty on purpose**: a description must come from
  `gemini-3.1-flash-lite`, not from whichever model happens to be idle. An explicit env
  override is the only way to change that, and it is a deliberate decision.
- `SUMMARIZER=mock` (or no `GEMINI_API_KEY`) selects the offline, deterministic describer.
  That is what tests run against.
- `GEMINI_THINKING_LEVEL` is blank by default, so no thinking config is sent (cheapest, and
  valid on every model). Use `minimal|low|medium|high` only if a description needs more
  reasoning — never a numeric thinking budget, which models from 3.5 onwards reject.
- Only two things call a model at all: **one call per folder** during Graph Creation, and
  **one call per placement** in Graph Add. Graph AI Search and Graph Add suggestions are local
  and make no model call — never "upgrade" them into a model call.

## Testing: at most 5 model requests per task

When **you (the AI agent)** run anything that can reach Gemini for real, the whole task gets
**at most 5 model requests in total**. This is a spend cap on the Gemini billing plan, not a
quota of the application.

- Offline is the default and costs nothing: `pytest`, `verify_search`,
  `verify_add_document`, `upload_directory --dry-run` and
  `verify_add_document_live --suggest-only` make **zero** model requests. Use them first.
- Count before you run: one folder = one request, one placement = one request, suggestions =
  zero. A `test_docs` upload (root + 2 folders) is 3 requests; `example_project` is 15
  folders, so it is **not** an allowed AI live test.
- Every attempt counts: retries, fallback models and repeat runs included.
- One live run, then read the output. Never re-run a live verifier "to see if it worked".
- If a task genuinely needs more than 5 requests, **stop and ask the user** before the sixth.

## Users are not limited (for now)

No request counting, throttling or per-user quota belongs in the service code paths. A user of
the app may make as many calls as their work needs; `LLM_MIN_INTERVAL_SECONDS` exists to smooth
bursts, not to cap usage. Revisit this only when the user asks for it.
