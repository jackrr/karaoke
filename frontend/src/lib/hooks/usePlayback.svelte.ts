/**
 * usePlayback hook — manage playback position, seek, and state
 * for the currently playing track.
 */
import { currentTrack, queue } from '$lib/store';

export type PlaybackState = 'idle' | 'playing' | 'paused';

export interface PlaybackResult {
  position: number;
  state: PlaybackState;
  seek(pct: number): void;
  play(): void;
  pause(): void;
  toggle(): void;
  next(): void;
  prev(): void;
}

export function usePlayback(): PlaybackResult {
  let position = 0;
  let state = 'idle' as PlaybackState;

  return {
    get position() { return position; },
    get state() { return state; },

    seek(pct: number) {
      // Seek the currently playing <audio> element
      const audio = document.querySelector('audio');
      if (audio && audio.duration) {
        position = pct * audio.duration;
      }
    },

    play() {
      const audio = document.querySelector('audio');
      if (audio) {
        audio.play().catch(() => {});
        state = 'playing';
      }
    },

    pause() {
      const audio = document.querySelector('audio');
      if (audio) {
        audio.pause();
        state = 'paused';
      }
    },

    toggle() {
      if (state === 'playing') this.pause();
      else this.play();
    },

    next() {
      // Trigger next track via WebSocket
      // const { session } = session;
      // if (session) { /* send queue-skip message */ }
    },

    prev() {
      const audio = document.querySelector('audio');
      if (audio) {
        position = 0;
        audio.currentTime = 0;
      }
    },
  };
}
