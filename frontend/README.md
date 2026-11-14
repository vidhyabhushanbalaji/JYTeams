# frontend (placeholder)

The Electron desktop app will live here. It is intentionally empty for now: the backend
is built and agreed first, then the frontend is wired up to it.

When we start: Electron + Node 24 (`package.json` here), talking to the FastAPI service
at `http://localhost:8000` (see [`../backend/README.md`](../backend/README.md)). Add the
Electron renderer origin to `CORS_ORIGINS` in `backend/.env` when it exists.
