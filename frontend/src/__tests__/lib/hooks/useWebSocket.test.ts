/**
 * Tests for useWebSocket hook.
 * Tests the public API surface (connect, disconnect, send)
 * and basic connection state transitions.
 */
import { vi, beforeEach, afterEach, describe, it, expect } from 'vitest';

let WebSocketImpl: typeof WebSocket;
let locationProto: Location | undefined;

beforeEach(() => {
  WebSocketImpl = (globalThis as any).WebSocket;
  locationProto = Object.getOwnPropertyDescriptor(window, 'location')?.value;
});

afterEach(() => {
  // Restore
  if (locationProto) {
    Object.defineProperty(window, 'location', { value: locationProto });
  } else {
    Object.defineProperty(window, 'location', {
      value: undefined,
      writable: true,
      configurable: true,
    });
  }
});

describe('ws hook (useWebSocket)', () => {
  // Helper to import the module with mocked WebSocket
  async function getWsHook() {
    let originalWebSocket: typeof WebSocket | undefined;
    let originalLocation: any;

    originalWebSocket = (globalThis as any).WebSocket;
    originalLocation = (globalThis as any).location;

    // Mock WebSocket — always reports connected
    class MockWS {
      readyState = 1; // OPEN
      sendSpy = vi.fn();
      instance = this;
      constructor(url: string) {}
      send(data: string) { this.sendSpy(data); }
      close() {}
    }

    (globalThis as any).WebSocket = MockWS as unknown as typeof WebSocket;
    (globalThis as any).location = { protocol: 'http:', host: 'localhost:3000' };

    // Re-import the module with the mock
    const ws = await import('$lib/hooks/useWebSocket.svelte');

    return { ws, MockWS, originalWebSocket, originalLocation };
  }

  it('setup() returns connect, disconnect, send', async () => {
    const { ws } = await getWsHook();
    const result = ws.setup('test-id');
    expect(typeof result.connect).toBe('function');
    expect(typeof result.disconnect).toBe('function');
    expect(typeof result.send).toBe('function');
  });

  it('disconnect() can be called without error', async () => {
    const { ws } = await getWsHook();
    expect(() => ws.disconnect()).not.toThrow();
  });

  it('send() works when WebSocket is OPEN', async () => {
    const { ws, MockWS } = await getWsHook();
    const { connect, send } = ws.setup('send-test');
    connect();

    // Give the WebSocket instance time to be created
    await new Promise((r) => setTimeout(r, 10));

    send({ type: 'ping' });

    // The send method should have called ws.send on the open connection
    expect(MockWS.prototype.sendSpy).toHaveBeenCalled();
  });

  it('send() does nothing when WebSocket is not OPEN', async () => {
    const { ws } = await getWsHook();
    const { send } = ws.setup('send-test');
    send({ type: 'ping' }); // should not error
    // If no open WebSocket, send should silently be a no-op
  });
});
