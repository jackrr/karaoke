import { execSync } from 'child_process';
import { spawn } from 'child_process';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const PROJECT_ROOT = path.resolve(__dirname, '..');
const BACKEND_DIR = path.join(PROJECT_ROOT, 'backend');
const FRONTEND_DIR = path.join(PROJECT_ROOT, 'frontend');

const BACKEND_URL = 'http://localhost:8000/health';
const FRONTEND_URL = 'http://localhost:5173';
const HEALTH_CHECK_RETRIES = 20;
const HEALTH_CHECK_INTERVAL_MS = 1500;

function waitFor(url: string, name: string, retries: number = HEALTH_CHECK_RETRIES): Promise<void> {
  return new Promise((resolve, reject) => {
    const attempt = (retry: number) => {
      if (retry <= 0) {
        reject(new Error(`${name} failed to become ready after ${HEALTH_CHECK_RETRIES} attempts`));
        return;
      }
      fetch(url, { signal: AbortSignal.timeout(3_000) })
        .then(res => {
          if (res.ok) {
            console.log(`✅ ${name} ready at ${url}`);
            resolve();
          } else {
            setTimeout(() => attempt(retry - 1), HEALTH_CHECK_INTERVAL_MS);
          }
        })
        .catch(() => {
          setTimeout(() => attempt(retry - 1), HEALTH_CHECK_INTERVAL_MS);
        });
    };
    attempt(retries);
  });
}

export async function setup() {
  console.log('\n🚀 E2E Setup: Starting servers...\n');

  // ── Start backend ──
  console.log('  → Starting backend (FastAPI, :8000)...');
  const backendPtyMode = process.env.E2E_BACKEND_DIR || BACKEND_DIR;
  const backendPython = path.resolve(PROJECT_ROOT, 'venv', 'bin', 'python');
  console.log('  → Using python:', backendPython);
  const backendProc = spawn(
    'bash',
    ['-c', `cd ${backendPtyMode} && ${backendPython} -m uvicorn app.main:app --host 0.0.0.0 --port 8000`],
    { stdio: ['pipe', 'pipe', 'pipe'], env: { ...process.env, PYTHONUNBUFFERED: '1' } }
  );

  // Pipe backend logs for debugging
  backendProc.stdout?.on('data', (d) => process.stdout.write(`[backend] ${d}`));
  backendProc.stderr?.on('data', (d) => process.stderr.write(`[backend-err] ${d}`));
  backendProc.on('error', (err) => console.error('Backend failed to start:', err.message));

  await waitFor(BACKEND_URL, 'Backend');

  // ── Start frontend ──
  console.log('  → Starting frontend (Svelte/Vite, :5173)...');
  const frontendProc = spawn(
    'bash',
    ['-c', `cd ${FRONTEND_DIR} && bun run dev --port 5173`],
    { stdio: ['pipe', 'pipe', 'pipe'], env: { ...process.env, PYTHONUNBUFFERED: '1' } }
  );

  frontendProc.stdout?.on('data', (d) => process.stdout.write(`[frontend] ${d}`));
  frontendProc.stderr?.on('data', (d) => process.stderr.write(`[frontend-err] ${d}`));
  frontendProc.on('error', (err) => console.error('Frontend failed to start:', err.message));

  await waitFor(FRONTEND_URL, 'Frontend');

  console.log('\n✅ All servers up. Running tests...\n');

  // Store process references globally for teardown
  (global as unknown as Record<string, unknown>).backendProc = backendProc;
  (global as unknown as Record<string, unknown>).frontendProc = frontendProc;
}

export default setup;
