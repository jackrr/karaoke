import { getClientId } from "./identity";

const API_BASE = "/";

async function json<T>(res: Response): Promise<T> {
  return res.json();
}

// ---- HTTP helpers ----

export async function listSessions() {
  const res = await fetch(`${API_BASE}sessions`);
  if (!res.ok) throw new Error("Failed to list sessions");
  return json<{ sessions: Array<{ id: string; name: string }> }>(res);
}

export async function createSession(name: string, displayName: string) {
  const res = await fetch(`${API_BASE}sessions`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      name,
      display_name: displayName,
      client_id: getClientId(),
    }),
  });
  if (!res.ok) throw new Error("Failed to create session");
  return json<{
    id: string;
    name: string;
    passcode: string;
    host_client_id: string;
    client_id: string;
  }>(res);
}

export async function joinSession(passcode: string, displayName: string) {
  const res = await fetch(`${API_BASE}sessions/join`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      passcode,
      display_name: displayName,
      client_id: getClientId(),
    }),
  });
  if (!res.ok) throw new Error("Failed to join session");
  return json<{
    id: string;
    name: string;
    client_id: string;
    is_host: boolean;
  }>(res);
}

export async function getSession(id: string) {
  const res = await fetch(`${API_BASE}sessions/${id}`);
  if (res.status === 404) return null;
  if (!res.ok) throw new Error("Failed to get session");
  return json<{
    id: string;
    name: string;
    created_at: string;
    online: number;
    passcode: string;
    host_client_id: string;
    participants: Array<{
      client_id: string;
      display_name: string;
      is_host: boolean;
    }>;
  }>(res);
}

export async function leaveSession(id: string) {
  const res = await fetch(`${API_BASE}sessions/${id}/leave`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ client_id: getClientId() }),
  });
  if (!res.ok && res.status !== 204) {
    throw new Error("Failed to leave session");
  }
}

// ---- WebSocket helpers ----

export function createSessionWebSocket(
  sessionId: string,
  opts?: {
    onMessage?: (msg: { type: string; data: unknown }) => void;
    onOpen?: () => void;
    onClose?: () => void;
  },
) {
  const protocol = location.protocol === "https:" ? "wss:" : "ws:";
  const clientId = getClientId();
  const ws = new WebSocket(
    `${protocol}//${location.host}/ws/${sessionId}?client_id=${encodeURIComponent(clientId)}`,
  );
  let connected = false;

  ws.onopen = () => {
    connected = true;
    opts?.onOpen?.();
  };

  ws.onclose = () => {
    connected = false;
    opts?.onClose?.();
  };

  ws.onmessage = (event) => {
    if (!connected) return;
    try {
      const msg = JSON.parse(event.data);
      opts?.onMessage?.(msg);
    } catch {
      // plain-text broadcast — treat as a "message" event
      opts?.onMessage?.({ type: "message", data: event.data });
    }
  };

  return {
    send: (type: string, data: unknown) => {
      ws.send(JSON.stringify({ type, data }));
    },
    get connected() {
      return ws.readyState === WebSocket.OPEN;
    },
    close: () => ws.close(),
    get readyState() {
      return ws.readyState;
    },
  };
}
