# JYTeams desktop app

Electron + React desktop client for the JYTeams backend. It does three things: show your
projects, draw one project as a movable graph of folders and documents, and let you add a
document or search for one using the Graph Add and Graph AI Search endpoints.

Visual direction: Microsoft Teams bones (rail, top bar, side panel) with a monochrome,
Notion-like skin. White paper, one grey ramp, ink for emphasis, no chromatic accent except
the error red.

## Prerequisites

- Node 24 and npm (the repo was built against Node 24.21 / npm 12).
- The backend running at <http://127.0.0.1:8000> (see [`../backend/README.md`](../backend/README.md)).
  With `AUTH_MODE=dev` the app sends no identity header and the backend falls back to its
  own `DEV_USER_ID`, so nothing has to be configured to start.

## Commands

```powershell
# from frontend/
npm install          # first time only
npm run dev          # Vite dev server + Electron with HMR
npm run typecheck    # tsc --noEmit for the main/preload project and the renderer project
npm test             # vitest: the graph rules and the formatters
npm run build        # production bundles into out/
npm run dist:win     # NSIS installer (must run on Windows)
npm run dist:mac     # DMG, arm64 + x64 (must run on macOS)
```

A smoke check that does not need a human at the window:

```powershell
$env:JYTEAMS_SMOKE='1'
.\node_modules\electron\dist\electron.exe .
```

It opens the app, clicks the first project, expands one folder, drags a card, round-trips a
layout through IPC, prints the result as JSON, then quits. Useful in CI, and it is what
proved the graph wiring while this was built. (Synthetic PointerEvents do not reliably
start React Flow\'s d3-drag, so it reports whether the card is draggable and whether the
position store round-trips rather than pixel movement.)

## How it talks to the backend

**Every HTTP call happens in the Electron main process** (`src/main/api/`), and the renderer
only receives JSON through the preload bridge (`window.jyteams`, typed by
`src/shared/types.ts`).

That is deliberate:

- a packaged window is a `file://` origin, so a direct fetch from the renderer would be
  rejected by CORS. Avoiding that means **no change to `CORS_ORIGINS`** is needed;
- a whole folder can be read from disk and streamed into a multipart upload without
  crossing IPC or holding 200 MB in the renderer;
- the bearer token (when one is used) never reaches page JavaScript.

`src/shared/types.ts` mirrors the pydantic schemas field for field. If a backend model
changes, that file changes with it and `npm run typecheck` finds the fallout.

Configuration lives in `config.json` in Electron's userData directory (set from Settings):
backend address, an optional dev user id, an optional bearer token. Nothing secret is kept
in the repository.

## The screens

1. **Projects** - white page, filter field, one row per project (name, description, date),
   and **New project**.
2. **New project** - name the project, pick a folder, review exactly what will be sent
   (markdown count, size, skipped files, limit warnings), then follow the background job:
   `queued -> summarising -> persisting -> ok / partial / failed`, polled every 1.5 s.
3. **Project** - the graph on a quiet dotted canvas, with a right-hand inspector. The top
   bar carries the project name, the search field, **Tidy layout** and **Add document**.
4. **Add document** - the two-step wizard the backend expects: choose a file, read the
   ranked suggestions (score, reason, counts, duplicate-content and name-clash warnings),
   choose *this folder* or *a new folder under it*, then place it. A `409` offers the free
   names the API returned as one-click chips; a `410` says the suggestion expired and
   starts again.
5. **Search** - runs Graph AI Search and lists ranked hits with score and reason; matching
   cards are outlined on the canvas, the folders the walk opened are marked, and everything
   else dims. Clicking a hit expands the ancestors it needs and centres the file.

## The graph rules

`src/renderer/src/lib/treeToGraph.ts` is the only place the visible set is decided:

- the tree is read once with `GET /projects/{id}/tree?depth=3`, which returns the root and
  **two further tiers of folders**;
- the root is always open, every deeper folder starts collapsed;
- a folder's files appear only when that folder is expanded - so the canvas opens calm and
  never draws a fourth tier on its own;
- expanding a folder uses the files already in the payload when it can, and calls
  `GET /directories/{id}` only when the depth-limited read hid its children (or after a
  placement changed the tree).

Positions are per project: dagre lays the visible graph out left-to-right, and anything you
drag is stored in `userData/layouts/<project>.json` and takes priority over the layout.
**Tidy layout** clears them and re-runs dagre.

## Design system

`src/renderer/src/styles/tokens.css` holds the whole scale: paper `#FFFFFF`, surface
`#F7F7F5`, hairline `#E8E8E4`, ink `#191919`, muted `#787774`. One UI type family plus one
mono family, reserved for paths, ids, sizes and scores. Motion is 120-180 ms, drags track
the pointer 1:1, and everything collapses to a cross-fade under `prefers-reduced-motion`.

Four skills were installed into `../.cline/skills/` and informed the work:
`frontend-design`, `web-design-guidelines`, `apple-design` (drag and momentum) and
`vercel-react-best-practices`.

## Layout

```text
src/
├─ shared/types.ts        # the API contract, shared by all three processes
├─ main/
│  ├─ index.ts            # window, macOS/Windows chrome, dev console bridge, smoke check
│  ├─ ipc.ts              # one channel per API call
│  ├─ config.ts           # backend address + identity, in userData
│  ├─ layout.ts           # per-project card positions
│  ├─ api/                # fetch wrapper, endpoint calls, error normalisation
│  └─ fs/walk.ts          # folder walk: markdown only, POSIX relative paths, limits
├─ preload/               # contextBridge surface + its .d.ts
└─ renderer/src/
   ├─ lib/                # treeToGraph, layout, format, errors (pure, unit tested)
   ├─ state/              # useProjectGraph, useProjects, useSearch, usePositions, useToasts
   ├─ components/         # rail, home, project, canvas, nodes, inspector, the two flows
   └─ styles/             # tokens.css, app.css
```

## Decisions worth knowing

- **Electron is pinned to `~40.10.2`.** Electron 45/44 depend on
  `@electron-internal/extract-zip`, whose published package in this environment only ships
  the darwin binary, so its postinstall cannot extract the Windows zip. 40.10.x uses the
  pure-JS `extract-zip` and installs cleanly. Bump it once that package is fixed.
- **npm 12 blocks install scripts by default.** Electron's postinstall did not run, so the
  binary was fetched with `node node_modules/electron/install.js`. On a fresh clone do the
  same if the app will not start.
- **No file-content viewer.** The backend exposes summaries and descriptions, not document
  bodies, so the app shows those.
- **Search and add are slow on purpose.** Both are real model walks; the UI treats them as
  deliberate actions with progress states rather than typing-time suggestions.
- **No login screen.** The app speaks to `AUTH_MODE=dev` today; a bearer token can be pasted
  into Settings for `AUTH_MODE=supabase`, but a real sign-in flow is the next piece.
- **Packaging is configured, not signed.** `electron-builder.yml` builds NSIS on Windows and
  DMG on macOS unsigned; signing/notarisation needs certificates and must run on each OS.