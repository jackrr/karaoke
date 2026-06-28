import { execSync } from 'child_process';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const PROJECT_ROOT = path.resolve(__dirname, '..');

export async function teardown() {
  console.log('\n🧹 E2E Teardown: Shutting down servers...');

  const backendProc = (global as unknown as Record<string, unknown>).backendProc;
  const frontendProc = (global as unknown as Record<string, unknown>).frontendProc;

  let exited = 0;
  let total = 2;

  const stop = (name: string, child: unknown) => {
    if (!child) {
      ++exited;
      console.log(`  → ${name}: already exited`);
      return;
    }

    const proc = child as ReturnType<typeof import('child_process').spawn>;
    if (proc.pid) {
      try {
        process.kill(-proc.pid, 'SIGTERM'); // kill process group
        // Give it a moment to shut down gracefully
        setTimeout(() => {
          try { process.kill(-proc.pid, 'SIGKILL'); } catch {}
        }, 3000).unref();
        console.log(`  → ${name}: sent SIGTERM`);
      } catch {
        // Already exited
      }
    }
    ++exited;
  };

  stop('Backend', backendProc);
  stop('Frontend', frontendProc);

  // Poll for shutdown
  const poll = setInterval(() => {
    if (exited >= total) {
      clearInterval(poll);
      console.log('✅ Servers shut down.\n');
    }
  }, 500);

  // Timeout guard
  setTimeout(() => clearInterval(poll), 15_000).unref();
}

export default teardown;
