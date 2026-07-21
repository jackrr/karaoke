# Karaoke

A little web app for doing karaoke as a group.

## Features (WIP)

- **Sessions** — Create a room or join an existing one via 6-digit passcode
- **Queue management** — Enqueue and list tracks (remove/reorder not yet implemented)
- **Track sources** — YouTube URL (audio file upload not yet implemented)
- **Real-time sync** — WebSocket broadcasts for queue, track, and client state
- **Stem separation** — Upon enqueue, vocals are stemmed out (via Demucs) then re-added at a configured reduction in volume
- **Lyrics** — Upon enqueue, lrc format lyrics are fetched from lrclib.net, falling back to YouTube captions converted to lrc format. Lyrics are shown in sync with the played track.
- **Track streaming** - The playback view streams the modified currently active track and lyrics from the server

## Tech

- Frontend: Bun + SvelteKit
- Backend: Python + FastAPI + sqlite
- E2E tests: Playwright (`e2e/`)

## How to Run

### Backend

```bash
cd backend && uv sync
uv run fastapi dev app/main.py
```

The API runs at **http://localhost:8000**. A SQLite database (`karaoke.db`) is created automatically when the app starts.

### Frontend (Bun + Svelte)

```bash
cd frontend
bun install
bun run dev
```

The dev server runs at **http://localhost:5173**.

### E2E tests

```bash
cd e2e
bun install
bun run test
```

### Combined build + serve

```bash
./scripts/serve
```

Builds the frontend and serves it alongside the backend from a single FastAPI process at **http://localhost:8765**.

### Backend configuration

The backend reads settings from environment variables (or a `.env` file in `backend/`), including `database_path`, `storage_dir`, `vocal_volume_fraction` (vocal volume in the remixed track, default `0.20`), and `demucs_model` (default `htdemucs`).
