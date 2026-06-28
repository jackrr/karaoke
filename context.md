# Karaoke Project — Full Context

## Project Summary

A **session-based karaoke webapp** where hosts enqueue tracks (via upload, or pending Jellyfin/Youtube support), and guests join via a 6-digit passcode. Synchronized lyrics and audio streaming to connected clients via WebSocket. SQLite persistence for all state.

### Tech Stack
| Layer | Technology |
|-------|------------|
| Backend | FastAPI (Python), aiosqlite, pydantic, pydantic-settings |
| Frontend | SvelteKit + Bun, Tailwind CSS |
| WebSocket | FastAPI built-in WebSocket |
| Testing | Playwright (E2E) |
| Audio processing | Stub: pyacoustid, Demucs, yt-dlp, LRCLib (not implemented) |

### Current Implementation Status
- **Phase 1 (Foundation)**: ✅ Complete — sessions, passcodes, WebSocket connection with reconnection (exponential backoff 1→16s), SQLite persistence
- **Phase 2 (Queue)**: ⚠️ Mostly complete — CRUD works, broadcast works, but **no role enforcement** on any mutable endpoint
- **Phase 3 (Processing)**: ❌ All stubs — downloader, acoustid, lrclib, demucs all return placeholder data; processing.py empty except for a class skeleton
- **Phase 4 (Playback)**: ❌ No audio streaming endpoint (HTTP range requests); no `<audio>` element in Svelte; LyricDisplay.svelte has no sync logic
- **Phase 5 (Jellyfin)**: ❌ Client skeleton exists; no enqueue route

## Directory Structure

```
karaoke/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app entry; lifespan; mounts /api/* and /ws/*
│   │   ├── __init__.py          # lifespan import; sets app.state.db, app.state.settings, etc.
│   │   ├── config.py            # Pydantic Settings with KARAOKE_ env prefix
│   │   ├── db.py                # SQLite layer (aiosqlite) — schema + indexes defined here
│   │   ├── sessions.py          # Create/join/expire sessions; client tracking
│   │   ├── queue.py             # Queue CRUD functions (enqueue, reorder, remove, clear, advance)
│   │   ├── track_service.py     # Stub service — get_streams, update_track_status, get_stream
│   │   ├── tracking.py          # Playback state (in-memory dict) + StreamingClientManager stub
│   │   ├── processing.py        # AudioProcessingPipeline class (mostly stub)
│   │   ├── jellyfin_client.py   # JellyfinClient class (Connect/Auth/Browse/Search/Stream)
│   │   ├── db_recovery.py       # RecoveryHelper class (stub)
│   │   ├── schema.py            # All Pydantic models (Session, Client, Track, QueueEntry, etc.)
│   │   ├── __init__.py          # lifespan context manager
│   │   ├── api/
│   │   │   ├── __init__.py      # get_api_router()
│   │   │   └── routes/
│   │   │       ├── __init__.py  # get_api_router() with all sub-routers
│   │   │       ├── sessions.py  # POST /api/sessions, POST /api/sessions/join, GET /api/sessions/{passcode}, GET /api/sessions/{id}/clients
│   │   │       ├── queue.py     # POST /api/queue/enqueue, PUT /api/queue/{id}/reorder, DELETE /api/queue/{id}, POST /api/queue/clear, GET /api/queue/{passcode}
│   │   │       ├── tracks.py    # GET /api/tracks, GET /api/tracks/{id}, POST /api/tracks/{id}/start, etc.
│   │   │       ├── upload.py    # POST /api/upload — accepts audio files
│   │   │       └── jellyfin.py  # GET /api/jellyfin/browse/{server}, GET /api/jellyfin/search/{server}, POST /api/jellyfin/stream
│   │   ├── utils/
│   │   │   ├── downloader.py    # Stub
│   │   │   ├── acoustid.py      # Stub
│   │   │   ├── lrclib.py       # Stub
│   │   │   └── demucs.py      # Stub
│   │   └── websocket/
│   │       ├── manager.py       # WebSocket connection management
│   │       └── schema.py        # WebSocket message schemas
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── app.svelte           # Root (delegates to +layout.svelte)
│   │   ├── routes/
│   │   │   ├── +layout.svelte   # SvelteKit layout
│   │   │   ├── +page.svelte     # Home page (create room / enter passcode)
│   │   │   └── room/
│   │   │       └── +page.svelte  # Room page
│   │   └── lib/
│   │       ├── components/
│   │       │   ├── EnqueueMenu.svelte
│   │       │   ├── index.ts           # Exports all components
│   │       │   ├── LyricDisplay.svelte
│   │       │   ├── NowPlayingBar.svelte
│   │       │   ├── PasscodeDisplay.svelte
│   │       │   ├── PlaybackView.svelte
│   │       │   ├── QueueList.svelte
│   │       │   ├── ReconnectBanner.svelte
│   │       │   └── Visualizer.svelte
│   │       ├── hooks/
│   │       │   ├── usePlayback.svelte.ts
│   │       │   ├── useSession.svelte.ts
│   │       │   └── useWebSocket.svelte.ts  # Reconnection with exponential backoff (1s→16s, 5 attempts), heartbeat (15s, dead=3), full-state snapshot on reconnect
│   │       ├── store.ts           # Session, queue, track, client stores
│   │       └── app.html
│   └── package.json
├── e2e/
│   ├── smoke.spec.ts
│   ├── global-setup.ts
│   ├── global-teardown.ts
│   └── playwright.config.ts
├── scripts/
│   └── e2e_setup.sh             # Orchestrates backend(:8000) + frontend(:5173) for E2E
├── IMPLEMENTATION_PLAN.md       # Detailed status of all phases, gaps, architecture
├── README.md
└── research.md
```

## Key Code — Backend

### 1. `backend/app/main.py` (lines 1-57)
FastAPI entry point. Mounts API router at `/api` and WebSocket at `/ws/{session_id}`. Lifespan sets `app.state.db`, `app.state.settings`, and creates `WebSocketManager`.

### 2. `backend/app/config.py` (lines 1-38)
Pydantic Settings with `KARAOKE_` env prefix. Key settings: `db_path`, `storage_root`, `demucs_device`, `max_concurrent_jobs`, `cors_origins`, `session_expiry_secs` (86400), `heartbeat_interval` (15s).

### 3. `backend/app/db.py` (lines 1-168)
SQLite layer with aiosqlite. Schema DDL in `SCHEMA_SQL`, indexes in `INDEX_SQL`. Module-level singleton `_db`. Key methods: `connect()`, `close()`, `query_one()`, `query_all()`, `execute()`. Migration: checks `sqlite_master` type='table' for `sessions` table.

**Tables**: `sessions`, `clients`, `queue_entries`, `tracks`, `processing_jobs`

### 4. `backend/app/sessions.py` (lines 1-147)
Session lifecycle: `generate_passcode()`, `create_session()`, `join_session()`, `get_session_by_passcode()`, `get_session_by_id()`, `expire_stale_sessions()`, `get_session_clients()`, `add_client()`, `remove_client()`. First joiner becomes host.

### 5. `backend/app/queue.py` (lines 1-157)
Queue CRUD: `enqueue()`, `reorder()`, `remove()`, `clear_session()`, `get_queue()`, `get_queue_by_passcode()`, `advance_to_next()`. Uses SQLite directly. **No role enforcement** — `added_by` / `client_id` are passed but never checked.

### 6. `backend/app/schema.py` (lines 1-145)
All Pydantic models in one file. Enums: `SessionStatus`, `ClientType`, `ConnectionState`, `TrackSource`, `TrackStatus`, `QueueStatus`, `ProcessingStage`. Models: `Session`, `Client`, `Track`, `QueueEntry`, `QueueEntryCreate`, `QueueReorder`, `ProcessingJob`, `QueueSnapshot`, `WSMessageType`, `WSMessage`, `PlaybackState`.

### 7. `backend/app/api/routes/queue.py` (lines 1-81)
Queue API routes. **Critical gap** — `enqueue_track()`, `reorder_track()`, `remove_track()`, `clear_queue()` do not check `client_type == "host"`. Accepts any client_id.

### 8. `backend/app/api/routes/sessions.py` (lines 1-77)
Session routes. `create_session_route` generates passcode via `secrets.token_urlsafe(6)[:6]` (NOT 6-digit numeric as per plan). `join_session_route` does not check client type.

### 9. `backend/app/tracking.py` (lines 1-128)
Playback state in memory via `_sessions: dict[str, _SessionState]`. Functions: `start_track()`, `pause()`, `seek()`, `tick()`, `get_session_state()`. **Writes to non-existent `sessions_playback` table**. `broadcast_state()` is a no-op. `StreamingClientManager` is an empty stub.

### 10. WebSocket Manager
Located at `backend/app/websocket/manager.py` — handles WS connection/disconnection, heartbeat (every 15s), and state broadcast to session clients.

### 11. `backend/app/processing.py` (lines 1-38)
`AudioProcessingPipeline.process()` calls stub utils (download_audio_from_yt, AcoustIDFingerprinter, LRCLIBClient, DemucsStemSplitter). All return placeholder data.

## Key Code — Frontend

### 1. `frontend/src/routes/+page.svelte` (lines 1-??)
Home page: "Create Room" → calls session creation API; "Enter Passcode" → join session API.

### 2. `frontend/src/routes/room/+page.svelte` (lines 1-??)
Room page: integrates queue list, now-playing bar, passcode display, visualizer, lyric display.

### 3. `frontend/src/lib/hooks/useWebSocket.svelte.ts` (lines 1-??)
WebSocket hook with reconnection strategy. States: IDLE → CONNECTING → CONNECTED → (disconnected) → RECONNECTING → CONNECTED or IDLE. Exponential backoff: 1s, 2s, 4s, 8s, 16s. Heartbeat: server pings every 15s; dead after 3 missed. On reconnect: requests full state snapshot.

### 4. `frontend/src/lib/hooks/useSession.svelte.ts` (lines 1-??)
Session management hook.

### 5. `frontend/src/lib/hooks/usePlayback.svelte.ts` (lines 1-??)
Playback hook — **needs `<audio>` binding**.

### 6. `frontend/src/lib/store.ts`
Svelte stores for session, queue, track, client state.

### 7. `frontend/src/lib/components/` key files
- `EnqueueMenu.svelte` — queue items list
- `LyricDisplay.svelte` — skeleton, no sync logic
- `NowPlayingBar.svelte` — skeleton
- `PasscodeDisplay.svelte` — shows passcode
- `PlaybackView.svelte` — skeleton
- `QueueList.svelte` — queue UI, needs drag & drop for reorder
- `ReconnectBanner.svelte` — shows reconnection status
- `Visualizer.svelte` — WebSocket visualizer

## Critical Gaps

1. **No audio streaming endpoint** — No `/api/tracks/{id}/stream` with HTTP range requests (`Range` → `206 Partial Content`)
2. **No `<audio>` HTML element** in Svelte — PlaybackView.svelte is empty stub
3. **No role enforcement** — `queue.py` routes accept mutations from any client ID, not just host. No `client_type == "host"` check
4. **No synced lyrics** — LyricDisplay.svelte is a skeleton; need `AudioTrackWithLyrics` with timestamped `{time, line}` pairs
5. **Processing pipeline is all stubs** — `downloader.py`, `acoustid.py`, `lrclib.py`, `demucs.py` return placeholders
6. **`tracking.py` writes to non-existent table** — `sessions_playback` table not in SCHEMA_SQL
7. **`broadcast_state()` is no-op** — Needs real-time WS broadcast to session clients
8. **`get_jellyfin_config()` always returns None** — Needs DB lookup or storage
9. **Passcode generation** — Uses `token_urlsafe(6)[:6]` (base64-like), not 6-digit numeric as per plan
10. **`enqueue` endpoint missing host_id** — Frontend sends `client_type` but no host_id passed

## Implementation Plan Status

| Phase | Status | Details |
|-------|--------|---------|
| 1. Foundation + Sessions | ✅ Complete | DB, schema, sessions CRUD, WebSocket, reconnection, heartbeat, frontend hooks |
| 2. Queue Service | ⚠️ Mostly Complete | CRUD works, broadcast works, but **no role enforcement** on any mutable endpoint |
| 3. Track Processing Pipeline | ❌ All Stubs | downloader.py, acoustid.py, lrclib.py, demucs.py all return placeholder data |
| 4. Playback + Synced Lyrics | ❌ Mostly Stubs | No audio streaming endpoint, no `<audio>` element, no lyric sync, `tracking.py` writes to nonexistent table |
| 5. Jellyfin + Polish | ❌ Mostly Stubs | Client skeleton exists; no enqueue route; `get_jellyfin_config()` always returns None |

## Key Architecture Decisions

- **SQLite as single source of truth** — All state persisted to SQLite tables defined in SCHEMA_SQL
- **In-memory playback state** — `_sessions` dict holds playback position; written back to DB on state changes (but to wrong table)
- **WebSocket for real-time** — Frontend uses exponential backoff reconnection; state snapshot on reconnect
- **Passcode-based joining** — 6-character code (currently base64, not numeric) for guest access
- **Host role on first join** — First client to join an empty session becomes host automatically
- **Queue position tracking** — Manual position management with SQLite UPDATEs for shift
- **Processing pipeline** — Designed as stages: download → identify → lyrics → stem → mix (all stub implementations)

# END
