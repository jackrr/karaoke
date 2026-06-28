/**
 * Tests for useSession hook.
 * Tests session creation and joining behaviour by mocking fetch().
 */
import { vi, beforeEach, afterEach, describe, it, expect } from 'vitest';
import { useSession } from '$lib/hooks/useSession.svelte';

// Capture the session and role store values for assertion
let capturedSession: Record<string, unknown> | null = null;
let capturedRole: string | null = null;

// We need raw store references from $lib/store to capture state.
// Instead of importing the writable (which triggers SvelteKit issues),
// we test via the hook's return values and the mock.

describe('useSession', () => {
  let fetchSpy: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    fetchSpy = vi.fn();
    globalThis.fetch = fetchSpy as unknown as typeof fetch;
    capturedSession = null;
    capturedRole = null;
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  // Basic smoke tests — the hook must be callable and return expected shape
  describe('initialisation', () => {
    it('returns an object with mode, error, createRoom, joinRoom, disconnect', () => {
      const { createRoom, joinRoom, disconnect } = useSession();
      expect(createRoom).toBeInstanceOf(Function);
      expect(joinRoom).toBeInstanceOf(Function);
      expect(disconnect).toBeInstanceOf(Function);
    });
  });

  describe('createRoom', () => {
    it('returns mode idle when successful', async () => {
      const sessionHook = useSession();
      fetchSpy.mockResolvedValue({
        ok: true,
        json: async () => ({ id: 'abc-123', passcode: '123456' }),
      });
      await sessionHook.createRoom();
      // The hook's `mode` getter should be 'idle' when done
      expect(sessionHook.mode).toBe('idle');
    });

    it('returns error message when fetch returns non-OK', async () => {
      const sessionHook = useSession();
      fetchSpy.mockResolvedValue({ ok: false });
      await sessionHook.createRoom();
      expect(sessionHook.error).toBe('Failed to create room. Try again.');
      expect(sessionHook.mode).toBe('idle');
    });

    it('returns error when fetch throws', async () => {
      const sessionHook = useSession();
      fetchSpy.mockRejectedValue(new Error('Network is offline'));
      await sessionHook.createRoom();
      expect(sessionHook.error).toBe('Network is offline');
      expect(sessionHook.mode).toBe('idle');
    });
  });

  describe('joinRoom', () => {
    it('returns mode idle when successful', async () => {
      const sessionHook = useSession();
      const mockSession = {
        id: 'abc-123',
        passcode: '123456',
        status: 'active' as const,
        created_at: Date.now(),
        updated_at: Date.now(),
        expires_at: Date.now() + 3600_000,
      };
      fetchSpy.mockResolvedValue({
        ok: true,
        json: async () => ({ session: mockSession, role: 'guest' as const }),
      });
      await sessionHook.joinRoom('123456');
      expect(sessionHook.mode).toBe('idle');
    });

    it('returns error when fetch returns non-OK', async () => {
      const sessionHook = useSession();
      fetchSpy.mockResolvedValue({ ok: false });
      await sessionHook.joinRoom('000000');
      expect(sessionHook.error).toBe('Room not found');
      expect(sessionHook.mode).toBe('idle');
    });

    it('returns error when fetch throws', async () => {
      const sessionHook = useSession();
      fetchSpy.mockRejectedValue(new Error('Network is offline'));
      await sessionHook.joinRoom('123456');
      expect(sessionHook.error).toBe('Failed to join — check your connection.');
      expect(sessionHook.mode).toBe('idle');
    });
  });

  describe('disconnect', () => {
    it('resets state cleanly', async () => {
      const sessionHook = useSession();
      await sessionHook.disconnect();
      expect(sessionHook.mode).toBe('idle');
    });
  });
});
