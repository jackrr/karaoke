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

The backend reads settings from environment variables (or a `.env` file in `backend/`), including `database_path`, `storage_dir`, `vocal_volume_fraction` (vocal volume in the remixed track, default `0.20`), `demucs_model` (default `htdemucs`), `demucs_device` (default `auto`), and `youtube_cookies_file` (path to a Netscape-format `cookies.txt`, used by yt-dlp when YouTube demands sign-in confirmation on some videos; unset by default).

## Deploying

The app ships as a single container image that serves the built frontend and the
API from one FastAPI process. The frontend calls the API with relative URLs, so
there is no base-URL or CORS configuration to set.

### Build

```bash
docker build -t karaoke .
```

CI builds `linux/amd64` and pushes to `ghcr.io/<owner>/karaoke` on every push to
`main` and on `v*` tags (`.github/workflows/image.yml`).

The image is about 3.3 GB compressed and ~9.5 GB unpacked, almost entirely
PyTorch and its bundled NVIDIA CUDA libraries. That is a one-time pull per host.

### Run

```bash
docker run -d --name karaoke \
  --gpus all \
  -p 8765:8000 \
  -v /srv/karaoke:/data \
  ghcr.io/<owner>/karaoke:latest
```

Or with Compose, which sets the same things up:

```bash
KARAOKE_DATA_DIR=/srv/karaoke docker compose up -d
```

`compose.yaml` pulls the published image by default and only falls back to
building from source, so the host needs a checkout of this repo only if you
intend to build there. `KARAOKE_PORT` overrides the published port (default
`8765`).

### Storage

Everything persistent lives under `/data` in the container:

| Path                 | Contents                                  |
| -------------------- | ----------------------------------------- |
| `/data/karaoke.db`   | SQLite database                           |
| `/data/storage`      | Downloaded audio, separated stems, lyrics |

Mount any host directory there. The two paths are independently configurable, so
the database can live outside the media volume if you'd rather:

```bash
docker run ... \
  -v /srv/karaoke:/data \
  -v /var/lib/karaoke:/db \
  -e DATABASE_PATH=/db/karaoke.db \
  ghcr.io/<owner>/karaoke:latest
```

Both directories are created on startup if they don't exist.

The container starts as root only long enough to take ownership of `/data`
(non-recursively), then drops to the unprivileged `app` user (UID 10001) for the
server process itself — so a freshly created host directory works without any
manual `chown`. Note that this does change the host directory's owner to UID
10001. To avoid that, pass `--user "$(id -u):$(id -g)"`; the entrypoint then
skips the ownership step entirely, and you are responsible for making the
directory writable by that user.

### Environment variables

| Variable                  | Default            | Meaning                                                     |
| ------------------------- | ------------------ | ----------------------------------------------------------- |
| `DATABASE_PATH`           | `/data/karaoke.db` | SQLite file. `:memory:` for an ephemeral database.           |
| `STORAGE_DIR`             | `/data/storage`    | Downloaded audio, stems, and lyrics.                         |
| `DEMUCS_DEVICE`           | `auto`             | `auto`, `cuda`, or `cpu`. See below.                         |
| `DEMUCS_MODEL`            | `htdemucs`         | Separation model. Only `htdemucs` weights are baked in.      |
| `VOCAL_VOLUME_FRACTION`   | `0.20`             | Vocal level in the remixed backing track.                    |
| `YOUTUBE_COOKIES_FILE`    | unset              | Netscape-format `cookies.txt` for videos that demand sign-in.|
| `SESSION_TTL_SECONDS`     | `21600`            | Idle time before a session and its tracks are reaped.        |
| `REAPER_INTERVAL_SECONDS` | `900`              | How often the reaper sweeps.                                 |
| `DEBUG`                   | `false`            | Verbose logging.                                             |

### GPU vs CPU

Vocal separation (demucs) is by far the most expensive thing the app does. On a
GPU it takes seconds per track; on CPU it takes minutes. The image supports both
and picks automatically.

**No `nvidia/cuda` base image is involved.** The CUDA userspace libraries
(cuBLAS, cuDNN, NCCL, the CUDA runtime) ship inside the PyTorch pip wheels. Only
the kernel driver comes from the host, injected at runtime by the NVIDIA
Container Toolkit. That is also why the image sets `NVIDIA_VISIBLE_DEVICES` and
`NVIDIA_DRIVER_CAPABILITIES` itself — an `nvidia/cuda` base would have preset
them, and without them the toolkit silently declines to inject the driver.

Host prerequisites for GPU:

- NVIDIA driver **525 or newer** (PyTorch 2.2.2 targets CUDA 12.1).
- `nvidia-container-toolkit` installed, then:
  ```bash
  sudo nvidia-ctk runtime configure --runtime=docker
  sudo systemctl restart docker
  ```

Then expose the GPU to the container:

- Docker: `--gpus all`
- Podman: `--device nvidia.com/gpu=all` (CDI)
- Compose: `gpus: all` (already in `compose.yaml`)

Verify it worked:

```bash
docker run --rm --gpus all ghcr.io/<owner>/karaoke:latest \
  python -c "import torch; print(torch.cuda.is_available())"
```

The app also logs GPU status on every startup — look for `CUDA available: True
(device: ...)`. If `DEMUCS_DEVICE` is `auto` and no GPU is found, it logs a
warning and falls back to CPU rather than refusing to start, so a broken GPU
degrades performance instead of taking the app down. Set `DEMUCS_DEVICE=cpu` to
force CPU explicitly, or `cuda` to fail loudly when the GPU is missing.

Running without a GPU needs no special flags — drop `--gpus all` and it works,
just slowly.

### Reverse proxy

Run exactly **one** worker (the image already does). The WebSocket connection
registry and the SQLite connection are in-process singletons, so a second worker
would see a different half of the state.

A TLS-terminating reverse proxy must forward WebSocket upgrade headers for
`/ws`, e.g. for nginx:

```nginx
location / {
    proxy_pass http://127.0.0.1:8765;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}
```
