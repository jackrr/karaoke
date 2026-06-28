import type { Session, QueueEntry, Track, Client, LyricsDisplay } from '$lib/store';

export interface WsMessage {
  type:
    | 'ping'
    | 'pong'
    | 'snapshot'
    | 'session'
    | 'updateQueue'
    | 'updateTrack'
    | 'updateClients'
    | 'updateLyrics'
    | 'recovery'
    | 'error'
    | 'enqueue';
  session?: Session;
  queue?: QueueEntry[];
  track?: Track;
  clients?: Client[];
  lyrics?: LyricsDisplay;
  role?: 'host' | 'guest';
  message?: string;
  payload?: {
    client_id?: string;
    source?: string;
    metadata?: unknown;
  };
}

export interface SetupResult {
  connect(): void;
  disconnect(): void;
  send(msg: Omit<WsMessage, 'type'> & { type: string }): void;
}

/* ---- internal constants / state ---- */

const WS_BASE = `${
  window.location.protocol === 'https:' ? 'wss' : 'ws'
}://${window.location.host}/api/ws`;

const MAX_RETRIES = 5;
const HEARTBEAT_MS = 15_000;
const HEARTBEAT_DEAD = 3;

let ws: WebSocket | null = null;
let retryCount = 0;
let retryTimer: ReturnType<typeof setTimeout> | null = null;
let heartbeatTimer: ReturnType<typeof setInterval> | null = null;
let deadPings = 0;

/* ---- public ---- */

export function setup(_wsId: string): SetupResult {
  return { connect, disconnect, send: sendMessage };
}

export function connect() {
  if (ws?.readyState === WebSocket.OPEN) return;

  ws = new WebSocket(WS_BASE);

  ws.onopen = () => {
    retryCount = 0;
    deadPings = 0;
    import('$lib/store').then((m) => (m.connectionState.set('connected')));
    startHeartbeat();
  };

  ws.onclose = (ev: CloseEvent) => {
    stopHeartbeat();
    retryCount++;
    import('$lib/store').then((m) => {
      if (retryCount <= MAX_RETRIES) {
        m.connectionState.set('reconnecting');
        const delay = Math.min(1000 * 2 ** (retryCount - 1), 16000);
        retryTimer = setTimeout(connect, delay);
      } else {
        m.connectionState.set('disconnected');
      }
    });
  };

  ws.onmessage = (evt: MessageEvent) => {
    try {
      const data = JSON.parse(evt.data) as WsMessage;
      deadPings = 0;

      if (data.type === 'ping') {
        // echo to keep server happy (optional)
        return;
      }

      Promise.resolve().then(() =>
        import('$lib/store').then((m) => dispatch(data, m))
      );
    } catch {
      /* ignore garbled messages */
    }
  };
}

export function disconnect() {
  retryCount = 0;
  stopHeartbeat();
  if (ws) {
    ws.close();
    ws = null;
  }
  import('$lib/store').then((m) => m.connectionState.set('disconnected'));
}

export function sendMessage(msg: Omit<WsMessage, 'type'> & { type: string }) {
  if (ws?.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify(msg));
  }
}

/* ---- helpers ---- */

function dispatch(data: WsMessage, m: typeof import('$lib/store')) {
  switch (data.type) {
    case 'snapshot':
    case 'recovery':
      m.session.set(data.session ?? m.session);
      m.queue.set(data.queue ?? m.queue);
      m.currentTrack.set(data.track ?? m.currentTrack);
      m.clients.set(data.clients ?? m.clients);
      m.role.set(data.role ?? m.role);
      if (data.lyrics) m.lyrics.set(data.lyrics);
      m.connectionState.set('connected');
      break;
    case 'session':
      m.session.set(data.session ?? m.session);
      break;
    case 'updateQueue':
      m.queue.set(data.queue ?? m.queue);
      break;
    case 'updateTrack':
      m.currentTrack.set(data.track);
      break;
    case 'updateClients':
      m.clients.set(data.clients ?? m.clients);
      break;
    case 'updateLyrics':
      m.lyrics.set(data.lyrics);
      break;
    case 'error':
      toast(data.message ?? 'An error occurred');
      break;
  }
}

function startHeartbeat() {
  stopHeartbeat();
  heartbeatTimer = setInterval(() => {
    if (ws?.readyState === WebSocket.OPEN) {
      deadPings++;
      if (deadPings >= HEARTBEAT_DEAD) disconnect();
    }
  }, HEARTBEAT_MS) as unknown as number;
}

function stopHeartbeat() {
  if (heartbeatTimer) {
    clearInterval(heartbeatTimer);
    heartbeatTimer = null;
  }
}

function toast(msg: string) {
  const el = document.createElement('div');
  Object.assign(el.style, {
    position: 'fixed',
    bottom: '16px',
    right: '16px',
    background: 'var(--bg-secondary)',
    color: 'var(--text-primary)',
    padding: '10px 20px',
    borderRadius: '10px',
    zIndex: '999',
    fontSize: '0.9rem',
    boxShadow: '0 4px 12px rgba(0,0,0,0.4)',
  });
  el.textContent = msg;
  document.body.appendChild(el);
  setTimeout(() => el.remove(), 4000);
}
