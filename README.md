# Karaoke

A little web app for doing karaoke as a group.

## Tech

- Frontend: Bun + SvelteKit
- Backend: Python + FastAPI + sqlite
- E2E tests: Playwright (`e2e/`)

## How to Run

### Backend

```bash
cd backend && uv sync
uv run fastapi dev app/main.py --reload-dir app
```

`--reload-dir app` keeps the dev server's auto-reload watcher scoped to source code. Without it, the watcher covers the whole `backend/` working directory, including `storage/` — so files yt-dlp/demucs write mid-download trigger a reload that kills the in-progress background task, leaving the track stuck in `downloading` forever.

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

The backend reads settings from environment variables (or a `.env` file in `backend/`), including `database_path`, `storage_dir`, `vocal_volume_fraction` (vocal volume in the remixed track, default `0.20`), `demucs_model` (default `htdemucs`), and `youtube_cookies_file` (path to a Netscape-format `cookies.txt`, used by yt-dlp when YouTube demands sign-in confirmation on some videos; unset by default).
