# 🎤 Karaoke — Implementation Plan

## ✅ Implementation Status

| Phase | Description | Status | Summary |
|-------|-------------|--------|---------|
| **Phase 1** | Foundation + Sessions | ✅ Complete | All sub-items implemented. API routes serve, WebSocket connects/disconnects, Svelte WebSocket store with reconnection is wired up. UI renders. |
| **Phase 2** | Queue Service | ⚠️ Mostly Complete | CRUD + broadcast + upload endpoints exist. UI component exists. **Role enforcement on API routes is missing** — enqueue/reorder/clear have no permission checks. |
| **Phase 3** | Track Processing Pipeline | ❌ All Skeletons | `downloader.py`, `acoustid.py`, `lrclib.py`, `demucs.py` all return stub data/paths. `processing.py` is an empty stub. No actual pipeline logic. |
| **Phase 4** | Playback + Synched Lyrics | ❌ Mostly Skeletons | Server heartbeat exists. No HTTP range-request streaming endpoint. No Svelte `<audio>` element (no `usePlayback` hook usage). `LyricDisplay.svelte` has no sync logic. No auto-advance. |
| **Phase 5** | Jellyfin + Polish | ❌ Mostly Skeletons | `jellyfin_client.py` has skeleton Connect/Auth/Browse/Search/Stream methods. No `/api/jellyfin/enqueue` route. No visualizer, expiration cleanup, or Docker config. |

---

## ❌ Critical Gaps

| Gap | Impact | Location |
|-----|--------|----------|
| **No role enforcement on API routes** | Any connected client can enqueue, reorder, clear queue. Guests have no protection. | `backend/app/queue.py` routes |
| **Processing pipeline is all stubs** | Tracks can be added to queue but never processed. `downloader.py`, `acoustid.py`, `lrclib.py`, `demucs.py` return placeholder data. `processing.py` is empty. | `backend/app/utils/`, `processing.py` |
| **No audio streaming endpoint** | Nothing to play. `/audio/{track_id}` HTTP range-request route doesn't exist. | Backend routes |
| **No Svelte audio player** | Room.svelte has no `<audio>` element, no position sync hook wired to `usePlayback`. | `Room.svelte` |
| **No LRCLib timed lyric sync** | `LyricDisplay.svelte` is a placeholder with no active-line detection or scroll logic. | `LyricDisplay.svelte` |
| **No session expiration** | No periodic cleanup of stale/gone sessions (24h inactivity). | `db.py` / `manager.py` |

---

## Project Overview

A **session-based karaoke webapp** where hosts enqueue tracks (YouTube, file upload, or Jellyfin library), and guests join via a **random 6-digit passcode**. Synchronized lyrics and audio stream to all connected clients in real-time. State is **persisted in SQLite** for durability across reboots.

---

## Tech Stack

| Layer | Choice | Rationale |
|-------|--------|-------|
| Backend | **FastAPI** (Python) | Async-native, WebSocket support, `pyacoustid`/Demucs ecosystem |
| Storage | **SQLite** (via `aiosqlite`) | Simple, durable, zero-config; survives reboots |
| Frontend | **Svelte + Bun** | Lightweight, fast dev loop, Svelte's reactivity ideal for real-time UI |
| WebSocket | FastAPI built-in | Real-time queue state + track transitions push |
| Audio Stemming | **Demucs** (CUDA optional) | Auto-detects `torch.cuda.is_available()`; falls back to CPU on OOM; configurable `demucs_device` override |
| Lyrics Source 1 | **LRCLib** (lrclib.net) | Fetched via acoustic ID match — highest quality |
| Lyrics Source 2 | YouTube .lrc/captions | Fallback when LRCLib has results (full scrollable text) |
| Download | **yt-dlp** | Actively maintained fork |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                  Frontend (Svelte + Bun)                       │
│        ┌──────────┐  ┌──────────┐  ┌──────────┐              │
│        │ Home    │  │ Room/    │  │ Playback │              │
│        │ (Join)  │  │ Queue    │  │ View     │              │
│        └────┬─────┘  └────┬─────┘  └────┬─────┘              │
│             │              │              │                   │
│             └─────────┬───┴───┬─────┘                       │
│                WebSocket (wss)                                │
└────────────────────────┼──────────────────────────── ───────┘
                          │
┌──────────────────────────────────────┼───────────────────────┐
│           Backend (FastAPI + SQLite)                              │
│   ┌──────────┐  ┌──────────┐  ┌──────────┐                     │
│   │ Session  │  │ Queue    │  │ Track     │                     │
│   │ Manager  │  │ Service  │  │ Lifecycle │                     │
│   └────┬─────┘  └────┬─────┘  └────┬─────┘                    │
│        │             │              │                          │
│        │     ┌───────┼─────────┐     │                         │
│        │     │  Audio Processing Pipeline                            │
│        │     │ [stubs only — no real pipeline]                 │       │
│        │     └───────┴───────┘     │                         │
│        └───┬───┴──────────────────┼─────────────┤       │
│            │               2. [skeleton]       │           │       │
│           ┌─┴──┐   ┌──┬─┐  │              │           │       │
│           │ SQ │   │P │J  │              │           │       │
│           │l ite DB│  c │ s │              │           │       │
│           │ ess│   │r │ s │              │           │       │
│           ├───┤   ├──┬─┘  │              │           │       │
│           │ess│   │y│    │              │           │       │
│           ├───┤   ├──┬─┐  │              │           │       │
│           │ess│   │  │  │  │              │           │       │
└───┬─────┬─┴──┴─────┴──┴──┴─┴─────────────┴──────────┴───────┘
  │
  │  (on disk: karaoke.db)
```

---

## Passcode-Based Session Model

### Join Mechanism
- Every session has a **random 6-digit numeric passcode** (e.g., `482916`)
- Passcode is **randomly generated** on session creation (from 1,000,000 possibilities — collision probability is negligible)
- Any user can type the passcode on the Home page to join
- No URL-based join links — the passcode is the shared secret

### Role Model
| Role | Permissions |
|------|------|
| **Host** | Creates the session (first joiner), enqueue, reorder, remove, clear queue |
| **Guest** | View queue, view playback, cannot enqueue or reorder |

### ⚠️ Note: Role Enforcement (Missing)
The API routes in `backend/app/queue.py` **do not enforce roles** on enqueue, reorder, remove, or clear endpoints. Any connected WebSocket client can perform host actions. This is the single biggest security gap in Phase 2.

### Session Lifecycle
1. First user on the Home page clicks "Create Room" → server creates a session with a random 6-digit passcode
2. Passcode is displayed prominently on screen with a "Copy" button
3. Other users type the passcode on the Home page to join
4. Session persists in SQLite; survives server restart
5. Session expires after 24h of inactivity (all sockets disconnected) — **not yet implemented**

---

## Data Model (SQLite)

**Status: All tables exist in `db.py` and match the plan.** The database has been created with the following schema:

### ✅ `sessions`
```sql
CREATE TABLE sessions (
    id            TEXT PRIMARY KEY,       -- UUID
    passcode      TEXT UNIQUE NOT NULL,   -- 6-digit numeric
    host_id       TEXT,                   -- WebSocket client_id of host
    status        TEXT NOT NULL DEFAULT 'active',
                                                -- 'active' | 'idle' | 'gone'
    created_at    INTEGER DEFAULT (strftime('%s', 'now')),
    updated_at    INTEGER DEFAULT (strftime('%s', 'now')),
    expires_at    INTEGER
);
```

### ✅ `queue_entries`
```sql
CREATE TABLE queue_entries (
    id             TEXT PRIMARY KEY,
    session_id     TEXT NOT NULL REFERENCES sessions(id),
    track_id       TEXT,                    -- FK or NULL while processing
    position       INTEGER NOT NULL,
    status         TEXT NOT NULL DEFAULT 'pending',
                                                -- 'pending' | 'processing' | 'ready' | 'error'
    added_by       TEXT NOT NULL,           -- client_id of enqueuer
    source         TEXT NOT NULL,           -- 'youtube' | 'upload' | 'jellyfin'
    metadata       TEXT,                    -- JSON: title, artist, duration, source_url
    added_at       INTEGER DEFAULT (strftime('%s', 'now')),
    FOREIGN KEY (track_id) REFERENCES tracks(id)
);
```

### ✅ `tracks`
```sql
CREATE TABLE tracks (
    id             TEXT PRIMARY KEY,
    hash           TEXT UNIQUE,             -- chromaprint fingerprint or source URL hash
    title          TEXT NOT NULL,
    artist         TEXT,
    duration       REAL,
    storage_path   TEXT,                    -- absolute path to final karaoke audio
    stem_files     TEXT,                    -- JSON: {instrumental: path, vocal_volume: 0.2}
    lyrics_format  TEXT DEFAULT 'none',     -- 'lrclib' | 'raw' | 'none'
    lyrics_source  TEXT,                    -- 'lrclib' | 'yt'
    lyric_lines    TEXT,                    -- JSON: [{time_ms, text}]
    fallback_text  TEXT,                    -- full raw lyrics for scrollable fallback
    status         TEXT NOT NULL DEFAULT 'processing',
                                                  -- 'processing' | 'ready' | 'error'
    created_at     INTEGER DEFAULT (strftime('%s', 'now')),
    UNIQUE(hash, title)
);
```

### ✅ `clients`
```sql
CREATE TABLE clients (
    client_id   TEXT PRIMARY KEY,
    session_id  TEXT NOT NULL REFERENCES sessions(id),
    client_type TEXT NOT NULL,             -- 'host' | 'guest'
    joined_at   INTEGER DEFAULT (strftime('%s', 'now')),
    connected   INTEGER DEFAULT 1,         -- 1=connected, 0=disconnected
    last_seen   INTEGER DEFAULT (strftime('%s', 'now'))
);
```

### ✅ `processing_jobs`
```sql
CREATE TABLE processing_jobs (
    id                TEXT PRIMARY KEY,
    queue_entry_id    TEXT REFERENCES queue_entries(id),
    stage             TEXT NOT NULL,       -- 'downloading' | 'identifying' | 'lyrics' | 'stemming' | 'mixing'
    progress          REAL DEFAULT 0.0,    -- 0.0 - 1.0
    started_at        INTEGER,
    finished_at       INTEGER,
    error             TEXT,                -- error message if FAILED
    device            TEXT                 -- 'cuda' | 'cpu' (recorded at job start)
);
```

### ✅ Indexes
All four indexes defined in the plan exist:
```sql
CREATE INDEX idx_queue_entries_session ON queue_entries(session_id, position);
CREATE INDEX idx_tracks_hash ON tracks(hash);
CREATE INDEX idx_clients_session ON clients(session_id);
CREATE INDEX idx_processing_queue ON processing_jobs(queue_entry_id);
```

---

## Service Modules (Backend)

### 1. `db.py` — SQLite Layer
- ✅ Async SQLite connection pool via `aiosqlite`
- ✅ Schema migration (`CREATE TABLE IF NOT EXISTS`)
- ❌ Session expiration cleanup (periodic task) — **not implemented**
- ✅ Persistence for all state: sessions, queue, tracks, clients

### 2. `sessions.py` — Session Manager
- ✅ Generate random 6-digit numeric passcode
- ✅ Create / lookup / expire sessions (session creation and lookup work)
- ✅ Map first-joiner → host role
- ✅ Client join via passcode validation

### 3. `queue.py` — Queue Service
- ✅ Enqueue items (file upload, with stub support for YouTube/Jellyfin metadata)
- ✅ Reorder / remove queue items
- ⚠️ **No role enforcement** — enqueue/reorder/clear are open to all clients
- ✅ Track transitions (current → next → play) — stub endpoints exist
- ✅ Persist to SQLite on every mutation
- ✅ WebSocket broadcast on changes

### 4. `track_service.py` — Track Lifecycle
All methods are **stubs** — no real pipeline logic:
- ❌ `process_youtube(url)` — no implementation
- ❌ `process_file(filepath)` — no real fingerprinting
- ❌ `process_jellyfin(jellyfin_url)` — no real streaming
- ❌ `identify_track(audio_file)` — acoustid.py returns stub data
- ❌ `fetch_lyrics(title, artist)` — lrclib.py returns stub data
- ❌ `separate_stems(audio_file)` — demucs.py returns stub paths
- ❌ `build_karaoke_mix(stems)` — no implementation
- ❌ `serve_audio(track_id)` — no HTTP range-request streaming endpoint

### 5. `jellyfin_client.py` — Jellyfin Integration
- ✅ Skeleton methods: Connect, Auth, Browse, Search, Stream (all using `aiohttp`)
- ❌ `/api/jellyfin/enqueue` route doesn't exist
- ❌ Methods contain stub logic — no real Jellyfin API calls yet

### 6. `processing.py` — Job Queue
- ❌ **Empty stub** — no job scheduling, no checkpoint logic, no concurrent job limiting
- ❌ Pipeline is all stubs in `utils/` (`downloader.py`, `acoustid.py`, `lrclib.py`, `demucs.py`)
- ❌ CUDA auto-detect, OOM fallback, `demucs_device` override — all TBD

### 7. `db_recovery.py` — Fault Recovery
- ❌ **Not implemented** (stub only, referenced but absent)

---

## WebSocket Client (Svelte): Fault Tolerance & Reconnection

The Svelte client **implements** WebSocket disconnect handling:

### Connection States
```
IDLE → CONNECTING → CONNECTED → (disconnected)
                         ↓
                  RECONNECTING (retry: 0..5, exponential backoff)
                         ↓
                  CONNECTED or IDLE (max retries exceeded)
```

### ✅ Reconnection Strategy
- **Exponential backoff**: 1s, 2s, 4s, 8s, 16s (max 5 attempts)
- **On reconnect**: requests full state snapshot from server → rebuilds local state
- **Heartbeat**: server pings every 15s; client considers connection dead after 3 missed pings
- **UI indicator**: ReconnectBanner.svelte shows "Reconnecting..." with retry count
- **Max retries exceeded**: shows "Connection lost" screen with manual retry button

### ✅ Recovery on Reconnect
- Sends `currentTime` to server on reconnect → server seeks audio stream to that position *(server-side seek not implemented — no playback endpoint)*
- Server responds with full state snapshot (queue, current track, client list)
- Local store is fully replaced — never holds queue state independently

### ✅ Error Handling
- Network error → exponential backoff retry
- Server error (5xx) → shows toast notification + retry
- Queue mutation rejected by server → undo local change + shows error toast
- Passcode rejected → returns to Home with "Room not found" message

---

## State Persistence & Recovery

### ✅ On Server Restart
1. ✅ Start HTTP + WebSocket servers
2. ✅ Open SQLite database → run schema migration (`CREATE TABLE IF NOT EXISTS`)
3. ✅ Scan `sessions` table for `active` / `idle` sessions
4. ✅ Scan `clients` table: stale `connected = 1` entries are stale → set `connected = 0`
5. ❌ `processing_jobs` recovery — `processing.py` doesn't exist, so no checkpoint resume logic

### ❌ On Crash During Processing
- Not possible to test — the pipeline is all stubs.

---

## Lyrics Rendering (Updated)

### Two Modes — No Auto-Scroll Options

| Mode | Display | Trigger |
|------|---------|---------|
| **Timed** (primary) | Line-by-line highlight synced to playback timestamp | LRCLib lyrics found (has timestamps) — **stub only** |
| **Manual Scroll** (fallback) | Full text displayed in a scrollable view | No LRCLib lyrics — **component not yet built** |

### ❌ Lyric Rendering Component
`LyricDisplay.svelte` is **empty/skeleton** — has no active-line detection, no scroll logic, no `currentTime` sync. Needs full implementation per the spec above.

---

## File / Directory Structure

### ✅ Actual Files (matching plan, noting stub vs real):

```
karaoke/
├── backend/
│   ├── app/
│   │   ├── main.py              # ✅ FastAPI entry + WebSocket routes (manager.py)
│   │   ├── config.py            # ✅ Settings (demucs path, cuda, storage root, etc.)
│   │   ├── __init__.py
│   │   ├── db.py                # ✅ SQLite layer — all tables + indexes created
│   │   ├── sessions.py          # ✅ Session manager + passcode logic
│   │   ├── queue.py             # ✅ Queue CRUD + WebSocket broadcast (NO role enforcement)
│   │   ├── track_service.py     # ❌ Skeleton — returns None for all methods
│   │   ├── jellyfin_client.py   # ⚠️ Skeleton — Connect/Auth/Browse/Search/Stream stubs
│   │   ├── processing.py        # ❌ Empty stub
│   │   ├── db_recovery.py       # ❌ Not found
│   │   ├── audio_models.py      # ✅ Data models/types
│   │   └── utils/
│   │       ├── downloader.py    # ❌ Stub — placeholder for yt-dlp
│   │       ├── acoustid.py      # ❌ Stub — returns placeholder data
│   │       ├── lrclib.py        # ❌ Stub — returns placeholder data
│   │       └── demucs.py        # ❌ Stub — returns placeholder paths
│   ├── requirements.txt
│   └── tests/
├── frontend/
│   ├── src/
│   │   ├── App.svelte
│   │   ├── pages/
│   │   │   ├── Home.svelte         # ✅ Create room / enter passcode
│   │   │   └── Room.svelte         # ✅ Full room UI: queue, now-playing, passcode
│   │   ├── components/
│   │   │   ├── PasscodeDisplay.svelte ✅ Fully implemented
│   │   │   ├── EnqueueMenu.svelte  # Need to confirm
│   │   │   ├── QueueList.svelte    # ✅ In Room.svelte — host drag, guest view
│   │   │   ├── PlaybackView.svelte # Need to confirm
│   │   │   ├── NowPlayingBar.svelte # Need to confirm
│   │   │   ├── LyricDisplay.svelte # ❌ Skeleton — no sync logic
│   │   │   ├── Visualizer.svelte   # ❌ Not implemented
│   │   │   └── ReconnectBanner.svelte # ✅ Implemented
│   │   ├── hooks/
│   │   │   ├── useWebSocket.svelte # ✅ Fully implemented with reconnection
│   │   │   ├── useSession.svelte   # ✅ Implemented
│   │   │   └── usePlayback.svelte  # ❌ Skeleton — needs <audio> binding
│   │   ├── lib/
│   │   │   └── store.ts            # ✅ Session, queue, track, client stores
│   │   ├── styles/
│   │   └── app.css
│   ├── package.json
│   ├── svelte.config.js
│   ├── vite.config.ts
│   └── tsconfig.json
├── requirements.txt
├── package.json
├── Dockerfile (optional, for containerized demucs)
└── README.md
```

---

## Implementation Phases

### Phase 1: Foundation + Sessions
- [✅] FastAPI scaffolding + SQLite schema (all tables + indexes)
- [✅] Session creation with random 6-digit passcode
- [✅] Client join via passcode validation
- [✅] WebSocket base (connect, disconnect, broadcast in websocket/manager.py)
- [✅] Basic Svelte app: Home.svelte, Room.svelte (full room UI: queue, now-playing, passcode)
- [✅] Svelte WebSocket store with reconnection (exponential backoff 1→16s, heartbeat dead=3, full-state snapshot on reconnect)
- [✅] **Acceptance met** — Create room → see passcode → guest joins → both connected

### Phase 2: Queue Service
- [✅] Queue CRUD in SQLite (enqueue, reorder, remove, clear, list)
- [✅] Queue WebSocket broadcast to session
- [❌] Role enforcement (host vs guest) — API routes have NO permission checks for enqueue/reorder/clear
- [✅] File upload endpoint (.mp3/.wav/.flac/.ogg/.m4a validation)
- [✅] QueueList component in Room.svelte (with host-only drag-to-reorder buttons, guest is view-only by design)
- [⚠️] **Acceptance met except for role enforcement** — Any client can reorder/enqueue without being host

### Phase 3: Track Processing Pipeline
- [❌] yt-dlp download — downloader.py references it but no actual subprocess call (placeholder)
- [❌] pyacoustid identification — acoustid.py returns stub data (placeholder)
- [❌] LRCLib API wrapper — lrclib.py returns stub data (placeholder)
- [❌] YouTube lyrics fallback — no implementation
- [❌] Demucs subprocess wrapper — demucs.py returns stub paths (placeholder)
- [❌] Karaoke mix builder — no implementation
- [❌] Processing job system with checkpoint + recovery — processing.py is empty (just a stub with no job scheduling)
- [❌] **Pipeline is all skeletons**

### Phase 4: Playback + Synched Lyrics
- [❌] Audio streaming endpoint with HTTP range requests — no `/audio/{track_id}` route
- [❌] Svelte audio player + progress sync — No `<audio>` element in Room.svelte, no usePlayback hook usage
- [❌] LRCLib timed lyric renderer — LyricDisplay.svelte has no sync logic
- [❌] Raw lyric scrollable fallback — no component for it
- [❌] Track transition handling (auto-advance)
- [✅] WebSocket heartbeat on server (manager.py sends ping every HEARTBEAT_MS=15s)
- [⚠️] **Only server heartbeat exists**

### Phase 5: Jellyfin + Polish
- [✅] Jellyfin API client (jellyfin_client.py has Connect, Auth, Browse, Search, Stream methods using aiohttp)
- [❌] Enqueue from Jellyfin library — `/api/jellyfin/enqueue` doesn't exist
- [❌] Audio visualizer (canvas spectrum) — no component
- [❌] Session expiration (24h inactivity) — no cleanup mechanism in db.py or manager.py
- [❌] Docker / deployment config
- [⚠️] **Only Jellyfin client skeleton exists**

---

## Risks & Mitigations

| Risk | Mitigation | Status |
|------|------|--------|
| **demucs is heavy / GPU-constrained** | CPU mode; CUDA auto-detected via `torch.cuda.is_available()`; fall back to CPU on OOM; configurable `demucs_device` override; log VRAM at startup; limit to 1-2 concurrent jobs | ❌ Stub only |
| LRCLib has no result for a track | Always fall back to YouTube lyrics + raw scrollable display | ❌ Not implemented |
| Concurrent demucs = massive RAM | Queue processing jobs; max 1-2 concurrent; use `--two-stems=vocal` to save VRAM | ❌ No job queue implemented |
| yt-dlp downloads are slow | Progress updates via WebSocket; background processing; cancel support | ❌ No real download pipeline |
| Server crash during processing | `processing_jobs` table tracks stage + progress; recovery on startup resumes from checkpoint; host can retry stuck jobs | ❌ `processing.py` is empty |
| WebSocket reconnect during playback | On reconnect, send audio `currentTime` to server → server seeks audio stream | ❌ No audio streaming endpoint |
| SQLite concurrency issues | `aiosqlite` handles async isolation; serialize writes via a single writer task | ✅ Handled |

---

## Acceptance Criteria (Full System)

| # | Criterion | Status |
|---|-----------|--------|
| 1 | **Create a room** → assigned random 6-digit passcode | ✅ |
| 2 | **Guest joins** → types passcode on Home → real-time queue visible | ✅ |
| 3 | **WebSocket survives disconnect** → reconnects with exponential backoff; state snapshot on reconnect | ✅ (client only — server seeks not built) |
| 4 | **State survives reboot** → queue + tracks + sessions loaded from SQLite on startup | ✅ |
| 5 | **Enqueue YouTube** → download → identify → separate → lyrics → ready | ❌ All stubs |
| 6 | **Enqueue local file** → same pipeline from local .mp3/.wav | ⚠️ Upload endpoint works; pipeline not |
| 7 | **Enqueue Jellyfin** → browse library → enqueue → play | ❌ No enqueue route, client stub only |
| 8 | **Lyrics synced** → timed when LRCLib available; manual scroll when raw | ❌ Neither implemented |
| 9 | **Reorder queue** → drag to reorder; broadcast to all guests | ✅ (but roles open — guests can reorder too) |
| 10 | **Track auto-advance** → play ends → next track loads & plays | ❌ No playback |
