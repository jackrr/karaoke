// Svelte writable stores for the karaoke app state.
import { writable, derived } from 'svelte/store';

// Connection state
export const connectionState = writable<'idle' | 'connecting' | 'connected' | 'reconnecting' | 'disconnected'>('idle');

// Current session
export interface Session {
  id: string;
  passcode: string;
  host_id?: string;
  status: 'active' | 'idle' | 'gone';
  created_at: number;
  updated_at: number;
  expires_at: number;
}
export const session = writable<Session | null>(null);

// Queue entries
export interface QueueEntry {
  id: string;
  session_id: string;
  track_id?: string;
  position: number;
  status: string;
  added_by: string;
  source: string;
  metadata?: Record<string, any>;
  added_at: number;
}
export const queue = writable<QueueEntry[]>([]);

// Current track
export interface Track {
  id: string;
  hash?: string;
  title: string;
  artist?: string;
  duration?: number;
  storage_path?: string;
  stem_files?: Record<string, any>;
  lyrics_format: string;
  lyrics_source?: string;
  lyric_lines?: Array<{time_ms: number; text: string}>;
  fallback_text?: string;
  status: string;
  created_at: number;
}
export const currentTrack = writable<Track | null>(null);

// Connected clients
export interface Client {
  client_id: string;
  session_id: string;
  client_type: string;
  joined_at: number;
  connected: number;
  last_seen: number;
}
export const clients = writable<Client[]>([]);

// Lyrics
export interface LyricLine {
  time_ms: number;
  text: string;
}
export interface LyricsState {
  type: 'timed' | 'raw';
  content: LyricLine[] | string;
  isTimed: boolean;
}
export const lyrics = writable<LyricsState>({ type: 'none', content: [], isTimed: false });

export const role = writable<'host' | 'guest' | null>(null);

// Host convenience accessor (read-only)
export const isHost = derived(role, ($role) => $role === 'host');

export type ConnectionState = 'idle' | 'connecting' | 'connected' | 'reconnecting' | 'disconnected';
export type LyricsDisplay = LyricsState;
export type { LyricLine };
