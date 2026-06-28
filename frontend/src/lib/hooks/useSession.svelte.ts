/**
 * useSession hook — create or join a karaoke session
 * and set up the local state for the Room view.
 */
import { connectionState, role, session } from '$lib/store';
import type { Session } from '$lib/store';

export type SessionMode = 'idle' | 'creating' | 'joining';

export function useSession(): {
  mode: SessionMode;
  error: string;
  createRoom(): Promise<void>;
  joinRoom(passcode: string): Promise<void>;
  disconnect(): void;
} {
  let mode = 'idle' as SessionMode;
  let error = '';

  return {
    get mode() { return mode; },
    get error() { return error; },

    async createRoom() {
      mode = 'creating';
      error = '';
      try {
        const res = await fetch('/api/sessions', { method: 'POST' });
        if (!res.ok) {
          error = 'Failed to create room. Try again.';
          mode = 'idle';
          return;
        }
        const data: { passcode: string; id: string } = await res.json();
        session.set({
          id: data.id,
          passcode: data.passcode,
          status: 'active',
          created_at: Date.now(),
          updated_at: Date.now(),
          expires_at: Date.now() + 3600_000,
        });
        role.set('host');
        connectionState.set('connected');
      } catch (e: unknown) {
        error = e instanceof Error ? e.message : 'Unknown error';
      }
      mode = 'idle';
    },

    async joinRoom(passcode: string) {
      mode = 'joining';
      error = '';
      try {
        const res = await fetch(`/api/sessions/join/${encodeURIComponent(passcode)}`);
        if (!res.ok) {
          error = 'Room not found';
          mode = 'idle';
          return;
        }
        const json: { session: Session; role: 'host' | 'guest' } = await res.json();
        session.set(json.session);
        role.set(json.role);
      } catch (e: unknown) {
        error = e instanceof Error ? e.message : 'Failed to join — check your connection.';
      }
      mode = 'idle';
    },

    disconnect() {
      session.set(null);
      role.set(null);
      connectionState.set('idle');
      mode = 'idle';
    },
  };
}
