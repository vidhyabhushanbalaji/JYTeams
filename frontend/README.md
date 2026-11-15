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
npm test             # vitest: the graph rules, the formatters and the payload adapters
npm run build        # production bundles into out/
npm run dist:win     # NSIS installer (must run on Windows)
npm run dist:mac     # DMG, arm64 + x64 (must run on macOS)
```

A smoke check that does not need a human at the window:

```powershell
$env:JYTEAMS_SMOKE='1'
.\node_modules\electron\dist\electron.exe .
```

It opens the app, clicks the first project, reports the wheel (cards, centre, crumbs and any
overlapping rectangles), drills into a folder, comes back, tidies, and round-trips a layout
through IPC - printing each result as JSON. Set JYTEAMS_SMOKE_DIR to also save a PNG after
every step, which is how the wheel was reviewed.

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
changes, that file changes with it and `npm run typecheck` finds the fallout *inside the
client*; the payload shapes themselves are pinned by `lib/payloads.test.ts`, whose fixtures
are the examples in [`../backend/README.md`](../backend/README.md).

Configuration lives in `config.json` in Electron's userData directory (set from Settings):
backend address, an optional dev user id, an optional bearer token. Nothing secret is kept
in the repository.

## The screens

1. **Projects** - white page, filter field, one row per project (name, description, date),
   and **New project**.
2. **New project** - name the project, pick a folder, review exactly what will be sent
   (markdown count, size, skipped files, limit warnings), then follow the background job:
   `queued -> summarising -> persisting -> ok / partial / failed` (the middle step is shown as
   *Describing*, because folders are described rather than files), polled every 1.5 s. A
   `partial` job still opens the project and reports the folders that could not be described in
   a toast.
3. **Project** - the graph on a quiet dotted canvas, with a right-hand inspector. The top
   bar carries the project name, the search field, **Tidy layout** and **Add document**.
4. **Add document** - the two-step wizard the backend expects: choose a file, read its
   model-free preview and the locally ranked suggestions (score, reason, matched terms,
   counts, duplicate-content and name-clash warnings), choose *this folder* or *a new folder
   under it*, then place it. Scoring calls no model; only the placement does, once. A `409`
   offers the free names the API returned as one-click chips; a `410` says the suggestion
   expired and starts again.
5. **Search** - runs Graph AI Search and lists ranked hits with score, the matched terms and
   an excerpt cut from the document itself; matching cards are outlined on the canvas and
   everything else dims. Clicking a hit expands the ancestors it needs and centres the file.
   The walk is local and read-only, so a search makes no model calls.

## The tree

One folder sits at the top. Its **files hang from short branches** just below it, its
**immediate subfolders from longer branches** further down, and nothing deeper is drawn until
you press a folder - once to select it (the panel on the right describes it) and again to open
it, which makes it the top of a new tree. **Back** (or any breadcrumb segment) returns to the
previous folder, and because positions are remembered per view, it returns to exactly the
layout you left.

`lib/focusGraph.ts` decides what a view contains (one folder, its direct files, its direct
subfolders - never grandchildren). `lib/treeLayout.ts` decides where the cards go:

- a single stem runs down `x = 0`, and **no child card is ever placed on it**, so a folder
  branch can travel past the whole file band without crossing a card;
- cards sit in rows of up to four, at `-174, +174, -474, +474`, and every card is nudged by a
  small offset derived from a hash of its id - hand-placed to look at, but identical on every
  render, session and machine, so nothing re-shuffles under your cursor;
- `treeLayout.test.ts` lays out 300 id sets and asserts that no two rectangles intersect,
  that every card stays inside its jitter budget, that children sit below the centre, that
  the stem stays clear, and that the whole file band sits above the folder band.

Each branch is a cubic curve (`components/TreeEdge.tsx`) from the centre underside to the
child top. The control points turn late, so a short branch (a file) leaves the stem and
arrives almost at once while a long one (a folder) drops past the file band first. A seeded
sway and a 1.0-1.4 px stroke give every branch its own weight, and the geometry comes from
the live nodes, so a dragged card keeps its branch.

Dragging: nodes live in the React Flow store (`useNodesState` + `applyNodeChanges`), so a drag
updates one node object and only that card re-renders. Selection does not rebuild the array
either - it replaces at most the two cards whose flag changed - so nothing flickers and
nothing snaps back on drop.

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
   ├─ lib/                # focusGraph, treeLayout, format, errors (pure, unit tested)
   ├─ state/              # useFocusGraph, useProjects, useSearch, usePositions, useToasts
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
- **No layout library.** The tree is a row grid with a tested overlap guarantee, so
  @dagrejs/dagre was removed when the left-to-right tree went away.
