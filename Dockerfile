# syntax=docker/dockerfile:1

# Every stage pins linux/amd64 on purpose: torch only bundles CUDA wheels for
# that arch, so an image built on an arm64 machine would silently lose GPU
# support. Buildx warns about the constant; the warning is the intended tradeoff.
FROM --platform=linux/amd64 oven/bun:1.2.14 AS frontend
WORKDIR /src/frontend
COPY frontend/package.json frontend/bun.lock ./
RUN bun install --frozen-lockfile
COPY frontend/ ./
RUN bun run build


FROM --platform=linux/amd64 ghcr.io/astral-sh/uv:python3.11-bookworm-slim AS deps
ENV UV_PROJECT_ENVIRONMENT=/opt/venv \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy
WORKDIR /src/backend
# Lockfile-only layer: the multi-GB torch/nvidia install caches independently of app source.
COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project


FROM --platform=linux/amd64 python:3.11-slim-bookworm AS runtime

RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg libsndfile1 util-linux \
    && rm -rf /var/lib/apt/lists/*

ENV PATH=/opt/venv/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    TORCH_HOME=/opt/torch \
    HF_HOME=/opt/torch/huggingface \
    DATABASE_PATH=/data/karaoke.db \
    STORAGE_DIR=/data/storage \
    NVIDIA_VISIBLE_DEVICES=all \
    NVIDIA_DRIVER_CAPABILITIES=compute,utility

COPY --from=deps /opt/venv /opt/venv
COPY backend/pyproject.toml /app/backend/
COPY backend/app /app/backend/app
COPY --from=frontend /src/frontend/build /app/frontend/build

# Bake the htdemucs weights in so the first submitted track doesn't stall on a
# multi-hundred-MB download. Runs CPU-only, so a GPU-less builder is fine.
RUN python -c "from demucs.pretrained import get_model; get_model('htdemucs')"

# /opt/torch stays writable by the app user so a non-default DEMUCS_MODEL can
# still fetch its weights at runtime.
RUN useradd --create-home --uid 10001 app \
    && mkdir -p /data \
    && chown -R app:app /data /opt/torch

COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

WORKDIR /app/backend
EXPOSE 8000
ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=4)"

# Exactly one worker: the websocket manager and sqlite connection are in-process singletons.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--proxy-headers", "--forwarded-allow-ips", "*"]
