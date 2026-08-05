import { getClientId } from "./identity";

const API_BASE = "/";

async function json<T>(res: Response): Promise<T> {
  return res.json();
}

// ---- HTTP helpers ----

export async function listSessions() {
  const res = await fetch(`${API_BASE}sessions`);
  if (!res.ok) throw new Error("Failed to list sessions");
  return json<{ count: number }>(res);
}

export async function createSession(
  displayName: string,
  vocalVolumeFraction?: number,
) {
  const res = await fetch(`${API_BASE}sessions`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      display_name: displayName,
      client_id: getClientId(),
      ...(vocalVolumeFraction !== undefined && {
        vocal_volume_fraction: vocalVolumeFraction,
      }),
    }),
  });
  if (!res.ok) throw new Error("Failed to create session");
  return json<{
    id: string;
    code: string;
    host_client_id: string;
    client_id: string;
    vocal_volume_fraction: number;
  }>(res);
}

export async function joinSession(code: string, displayName: string) {
  const res = await fetch(`${API_BASE}sessions/join`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      code,
      display_name: displayName,
      client_id: getClientId(),
    }),
  });
  if (!res.ok) throw new Error("Failed to join session");
  return json<{
    id: string;
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
    code: string;
    created_at: string;
    online: number;
    host_client_id: string;
    participants: Array<{
      client_id: string;
      display_name: string;
      is_host: boolean;
    }>;
    now_playing_track_id: string | null;
    is_playing: boolean;
    vocal_volume_fraction: number;
  }>(res);
}

export async function updateSessionSettings(
  sessionId: string,
  vocalVolumeFraction: number,
) {
  const res = await fetch(`${API_BASE}sessions/${sessionId}/settings`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      client_id: getClientId(),
      vocal_volume_fraction: vocalVolumeFraction,
    }),
  });
  if (!res.ok) throw new Error("Failed to update session settings");
  return json<{ vocal_volume_fraction: number }>(res);
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

export type TrackStatus =
  | "pending"
  | "downloading"
  | "fetching_lyrics"
  | "stemming"
  | "downloaded"
  | "ready"
  | "error";

export type Track = {
  id: string;
  session_id: string;
  source_url: string;
  youtube_video_id: string;
  title: string | null;
  artist: string | null;
  status: TrackStatus;
  error_message: string | null;
  audio_path: string | null;
  lyrics_path: string | null;
  lyrics_source: string | null;
  duration_seconds: number | null;
  requested_by_client_id: string;
  requested_by_display_name: string | null;
  position: number;
  created_at: string;
  updated_at: string;
};

export class DuplicateTrackError extends Error {
  track: Track;
  constructor(track: Track) {
    super("Track already added to this session");
    this.name = "DuplicateTrackError";
    this.track = track;
  }
}

export async function submitYoutubeUrl(sessionId: string, url: string) {
  const res = await fetch(`${API_BASE}sessions/${sessionId}/tracks`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ url, client_id: getClientId() }),
  });
  if (res.status === 409) {
    const track = await json<Track>(res);
    throw new DuplicateTrackError(track);
  }
  if (!res.ok) throw new Error("Failed to submit YouTube URL");
  return json<Track>(res);
}

export async function listTracks(sessionId: string) {
  const res = await fetch(`${API_BASE}sessions/${sessionId}/tracks`);
  if (!res.ok) throw new Error("Failed to list tracks");
  const data = await json<{ tracks: Track[] }>(res);
  return data.tracks;
}

export function getTrackAudioUrl(sessionId: string, trackId: string): string {
  return `${API_BASE}sessions/${sessionId}/tracks/${trackId}/audio`;
}

export class LyricsNotAvailableError extends Error {}

export async function fetchTrackLyrics(
  sessionId: string,
  trackId: string,
): Promise<string> {
  const res = await fetch(
    `${API_BASE}sessions/${sessionId}/tracks/${trackId}/lyrics`,
  );
  if (res.status === 404)
    throw new LyricsNotAvailableError("No lyrics available");
  if (!res.ok) throw new Error("Failed to fetch lyrics");
  return res.text();
}

export async function reorderTracks(sessionId: string, trackIds: string[]) {
  const res = await fetch(`${API_BASE}sessions/${sessionId}/tracks/order`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ client_id: getClientId(), track_ids: trackIds }),
  });
  if (!res.ok) throw new Error("Failed to reorder tracks");
  const data = await json<{ tracks: Track[] }>(res);
  return data.tracks;
}

export async function removeTrack(sessionId: string, trackId: string) {
  const params = new URLSearchParams({ client_id: getClientId() });
  const res = await fetch(
    `${API_BASE}sessions/${sessionId}/tracks/${trackId}?${params}`,
    { method: "DELETE" },
  );
  if (!res.ok) throw new Error("Failed to remove track");
  const data = await json<{ tracks: Track[] }>(res);
  return data.tracks;
}

export async function updatePlaybackState(
  sessionId: string,
  trackId: string,
  isPlaying: boolean,
) {
  const res = await fetch(`${API_BASE}sessions/${sessionId}/playback`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      client_id: getClientId(),
      track_id: trackId,
      is_playing: isPlaying,
    }),
  });
  if (!res.ok) throw new Error("Failed to update playback state");
  return json<{ track_id: string; is_playing: boolean }>(res);
}

export async function requestPlayTrack(sessionId: string, trackId: string) {
  const res = await fetch(`${API_BASE}sessions/${sessionId}/playback/request`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ client_id: getClientId(), track_id: trackId }),
  });
  if (!res.ok) throw new Error("Failed to request playback");
  return json<{ track_id: string; requested_by_client_id: string }>(res);
}

// ---- WebSocket helpers ----

const RECONNECT_BASE_DELAY_MS = 1000;
const RECONNECT_MAX_DELAY_MS = 10000;

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
  const url = `${protocol}//${location.host}/ws/${sessionId}?client_id=${encodeURIComponent(clientId)}`;

  let ws: WebSocket;
  let closedByCaller = false;
  let reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  let reconnectDelay = RECONNECT_BASE_DELAY_MS;

  function scheduleReconnect() {
    if (closedByCaller || reconnectTimer) return;
    reconnectTimer = setTimeout(() => {
      reconnectTimer = null;
      connect();
    }, reconnectDelay);
    reconnectDelay = Math.min(reconnectDelay * 2, RECONNECT_MAX_DELAY_MS);
  }

  function connect() {
    // Each socket's handlers check `socket === ws` before acting, so a
    // superseded socket (e.g. one still CLOSING when visibilitychange forces
    // a fresh connect) can't fire a spurious onClose or schedule a
    // duplicate reconnect once it's no longer the current connection.
    const socket = new WebSocket(url);
    ws = socket;

    socket.onopen = () => {
      if (socket !== ws) return;
      reconnectDelay = RECONNECT_BASE_DELAY_MS;
      opts?.onOpen?.();
    };

    socket.onclose = () => {
      if (socket !== ws) return;
      opts?.onClose?.();
      scheduleReconnect();
    };

    socket.onmessage = (event) => {
      if (socket !== ws || socket.readyState !== WebSocket.OPEN) return;
      try {
        const msg = JSON.parse(event.data);
        opts?.onMessage?.(msg);
      } catch {
        // plain-text broadcast — treat as a "message" event
        opts?.onMessage?.({ type: "message", data: event.data });
      }
    };
  }

  connect();

  // A backgrounded tab's socket can die silently (mobile OSes especially)
  // without ever firing onclose until the tab is foregrounded again — check
  // and reconnect immediately on regaining visibility rather than waiting
  // out the backoff timer.
  function handleVisibilityChange() {
    if (
      !closedByCaller &&
      document.visibilityState === "visible" &&
      ws.readyState !== WebSocket.OPEN &&
      ws.readyState !== WebSocket.CONNECTING &&
      ws.readyState !== WebSocket.CLOSING
    ) {
      if (reconnectTimer) {
        clearTimeout(reconnectTimer);
        reconnectTimer = null;
      }
      connect();
    }
  }
  document.addEventListener("visibilitychange", handleVisibilityChange);

  return {
    send: (type: string, data: unknown) => {
      ws.send(JSON.stringify({ type, data }));
    },
    get connected() {
      return ws.readyState === WebSocket.OPEN;
    },
    close: () => {
      closedByCaller = true;
      if (reconnectTimer) clearTimeout(reconnectTimer);
      document.removeEventListener("visibilitychange", handleVisibilityChange);
      ws.close();
    },
    get readyState() {
      return ws.readyState;
    },
  };
}
