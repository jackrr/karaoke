#!/usr/bin/env bash
# e2e_setup.sh — Orchestrate server lifecycle for E2E testing.
# Usage:
#   ./e2e_setup.sh start    # Start both servers in background
#   ./e2e_setup.sh stop     # Kill both servers
#   ./e2e_setup.sh restart  # Stop + Start
#   ./e2e_setup.sh run      # Start → test → Stop (convenience)
#   ./e2e_setup.sh status   # Check server readiness

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

BACKEND_DIR="$PROJECT_ROOT/backend"
FRONTEND_DIR="$PROJECT_ROOT/frontend"

BACKEND_URL="http://localhost:8000/health"
FRONTEND_URL="http://localhost:5173"

BACKEND_PID_FILE="$PROJECT_ROOT/tmp/e2e.backend.pid"
FRONTEND_PID_FILE="$PROJECT_ROOT/tmp/e2e.frontend.pid"

mkdir -p "$PROJECT_ROOT/tmp"

# ── Helpers ────────────────────────────────────────────────────────────

wait_for_server() {
  local url="$1" name="$2" max_attempts="${3:-40}"
  for i in $(seq 1 "$max_attempts"); do
    if curl -sf "${url}" > /dev/null 2>&1; then
      echo "  ✅ $name ready ($url)"
      return 0
    fi
    sleep 0.5
  done
  echo "  ❌ $name failed to start within ${max_attempts}s" >&2
  return 1
}

# ── Commands ───────────────────────────────────────────────────────────

cmd_start() {
  echo "🚀 Starting E2E servers..."

  # Check port availability
  if ss -tln 2>/dev/null | grep -q ":8000 " && kill -0 "$(cat "$BACKEND_PID_FILE" 2>/dev/null)" 2>/dev/null; then
    echo "  ⏭ Backend already running"
  else
    echo "  → Starting backend (FastAPI, :8000)..."
    (cd "$BACKEND_DIR" && "$PROJECT_ROOT/venv/bin/python" -m uvicorn app.main:app --host 0.0.0.0 --port 8000) \
      >> "$PROJECT_ROOT/tmp/e2e.backend.log" 2>&1 &
    echo $! > "$BACKEND_PID_FILE"
    wait_for_server "$BACKEND_URL" "Backend" 40
  fi

  if ss -tln 2>/dev/null | grep -q ":5173 " && kill -0 "$(cat "$FRONTEND_PID_FILE" 2>/dev/null)" 2>/dev/null; then
    echo "  ⏭ Frontend already running"
  else
    echo "  → Starting frontend (Svelte/Vite, :5173)..."
    (cd "$FRONTEND_DIR" && bun run dev --port 5173) \
      >> "$PROJECT_ROOT/tmp/e2e.frontend.log" 2>&1 &
    echo $! > "$FRONTEND_PID_FILE"
    wait_for_server "$FRONTEND_URL" "Frontend" 40
  fi

  echo "✅ Both servers running."
}

cmd_stop() {
  echo "🧹 Stopping E2E servers..."

  local killed=0
  for pidfile in "$BACKEND_PID_FILE" "$FRONTEND_PID_FILE"; do
    local name
    name="$(basename "$pidfile" .pid)"
    pid="$(cat "$pidfile" 2>/dev/null || true)"
    if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
      echo "  → $name (PID $pid): SIGTERM → SIGKILL..."
      kill "$pid" 2>/dev/null || true
      sleep 0.5
      kill -9 "$pid" 2>/dev/null || true
      (( ++killed ))
    fi
    rm -f "$pidfile"
  done
  echo "✅ $killed server(s) stopped."
}

cmd_status() {
  echo "📊 Server status:"
  for pair in "$BACKEND_URL|Backend" "$FRONTEND_URL|Frontend"; do
    local url="${pair%%|*}" name="${pair##*|}"
    if curl -sf "${url}" > /dev/null 2>&1; then
      echo "  ✅ $name: $url ✓"
    else
      echo "  ❌ $name: $url ✗"
    fi
  done
}

cmd_run() {
  echo "🎬 Running E2E test suite...\n"
  cmd_start
  echo ""

  # Run playwright tests
  cd "$SCRIPT_DIR"
  npx playwright test smoke.spec.ts --reporter=line 2>&1
  local rc=$?
  
  cmd_stop
  echo ""
  if [ $rc -eq 0 ]; then
    echo "✅ All E2E tests passed!"
  else
    echo "❌ E2E tests failed (exit $rc)"
  fi
  return $rc
}

# ── Dispatch ───────────────────────────────────────────────────────────

case "${1:-help}" in
  start)   cmd_start ;;
  stop|down) cmd_stop ;;
  status)  cmd_status ;;
  run)     cmd_run   ;;
  test|tests) cmd_run   ;;
  help|--help|-h)
    cat <<EOF
Usage: $(basename "$0") {start|stop|status|run|help}

Commands:
  start   Start backend (:8000) + frontend (:5173) in background
  stop    Kill server processes
  status  Check which servers are reachable
  run     Start → run playwright smoke tests → stop
  help    Show this message

Environment overrides:
  E2E_BACKEND_DIR    Path to backend root (default: ./backend)
  E2E_FRONTEND_DIR   Path to frontend root (default: ./frontend)
EOF
    ;;
  *) echo "Unknown command: $1 (use --help)" >&2; exit 1 ;;
esac
