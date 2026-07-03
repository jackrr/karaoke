# Karaoke

A little web app for doing karaoke as a group.

## Features (WIP)

- **Sessions** — Create a room or join an existing one via 6-digit passcode
- **Queue management** — Enqueue, remove, reorder tracks
- **Track sources** — Audio file upload, YouTube URL
- **Real-time sync** — WebSocket broadcasts for queue, track, and client state
- **Stem separation** — Upon enqueue, vocals are stemmed out then re-added at a configured reduction in volume
- **Lyrics** — Upon enqueue, lrc format lyrics are fetched from lrclib.net. Lyrics are also downloaded in lrcformat for youtube files from captions. Lyrics are shown in sync with the played track.
- **Track streaming** - The playback view streams the modified currently active track and lyrics from the server

## Tech

- Frontend: Bun + Svelte
- Backend: Python + FastAPI + sqlite

## How to Run

### Backend

```bash
uv venv
cd backend && uv sync
uv run fastapi dev app/main.py
```

The API runs at **http://localhost:8000**. A SQLite database (`karaoke.db`) is created automatically when the app starts.

Backend dependencies are managed via [uv](https://docs.astral.sh/uv/) in `backend/pyproject.toml`.

### Frontend (Bun + Svelte)

```bash
cd frontend
bun install
bun run dev
```

The dev server runs at **http://localhost:5173**.
