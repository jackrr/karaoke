<script lang="ts">
  import { getSession, leaveSession, createSessionWebSocket, listTracks, submitYoutubeUrl, reorderTracks, removeTrack, type Track } from '$lib/api';
  import { getDisplayName } from '$lib/identity';
  import SessionCard from '$lib/components/SessionCard.svelte';
  import YoutubeDownloadForm from '$lib/components/YoutubeDownloadForm.svelte';
  import TrackPlayer from '$lib/components/TrackPlayer.svelte';
  import QueueList from '$lib/components/QueueList.svelte';
  import { goto } from '$app/navigation';
  import { onMount, onDestroy } from 'svelte';

  type Participant = { client_id: string; display_name: string; is_host: boolean };
  type SessionData = {
    id: string;
    code: string;
    online: number;
    host_client_id: string;
    participants: Participant[];
  };

  let session = $state<SessionData | null>(null);
  let loading = $state(true);
  let connected = $state(false);
  let sessionEnded = $state(false);
  let message = $state('');
  let messages = $state<Array<{ sender: string; text: string; type?: string }>>([]);
  let tracks = $state<Track[]>([]);
  let nowPlaying = $state<Track | null>(null);
  // Bumped every time `tracks` is replaced wholesale (queue_reordered
  // broadcasts, our own optimistic reorder). Svelte 5's `$state` wraps
  // assigned arrays in a new proxy on every write, so comparing an old array
  // reference to the current `tracks` by `===` does not reliably detect
  // "nothing else changed it since" — a plain version counter does.
  let tracksVersion = 0;
  let ws: ReturnType<typeof createSessionWebSocket> | null = null;
  let sessionId = '';
  const displayName = getDisplayName();

  async function refreshSession() {
    const data = await getSession(sessionId);
    if (data) session = data;
  }

  onMount(async () => {
    sessionId = new URL(window.location.href).pathname.replace('/session/', '');
    const data = await getSession(sessionId);
    if (!data) {
      await goto(`/?error=${encodeURIComponent("That session doesn't exist — check the code and try again.")}`);
      return;
    }
    session = data;
    loading = false;
    tracks = await listTracks(sessionId);

    ws = createSessionWebSocket(sessionId, {
      onOpen: () => {
        connected = true;
      },
      onClose: () => {
        connected = false;
      },
      onMessage: (msg) => {
        const typed = msg as { type: string; data: any };
        if (typed.type === 'message' && typed.data?.text) {
          messages.push({ sender: typed.data.sender ?? 'unknown', text: typed.data.text, type: typed.type });
        } else if (typed.type === 'member_joined' || typed.type === 'member_left') {
          refreshSession();
        } else if (typed.type === 'track_added') {
          const added = typed.data as Track;
          const idx = tracks.findIndex((t) => t.id === added.id);
          if (idx === -1) {
            tracks.push(added);
          } else {
            tracks[idx] = added;
          }
        } else if (typed.type === 'track_updated') {
          const updated = typed.data as Track;
          const idx = tracks.findIndex((t) => t.id === updated.id);
          if (idx === -1) {
            tracks.push(updated);
          } else {
            tracks[idx] = updated;
          }
        } else if (typed.type === 'queue_reordered') {
          tracks = typed.data.tracks as Track[];
          tracksVersion++;
        } else if (typed.type === 'track_removed') {
          tracks = typed.data.tracks as Track[];
          tracksVersion++;
          if (nowPlaying && !tracks.some((t) => t.id === nowPlaying!.id)) {
            nowPlaying = null;
          }
        } else if (typed.type === 'session_ended') {
          // The server reaped this session (e.g. it sat idle past the TTL)
          // out from under us. Show a clear message instead of leaving the
          // UI looking connected to a session that no longer exists.
          sessionEnded = true;
          nowPlaying = null;
        }
      },
    });
  });

  async function handleSubmitTrack(url: string) {
    return submitYoutubeUrl(sessionId, url);
  }

  async function handleReorder(orderedIds: string[]) {
    const previousTracks = tracks;
    const byId = new Map(tracks.map((t) => [t.id, t]));
    const optimisticTracks = orderedIds.map((id) => byId.get(id)).filter((t): t is Track => t !== undefined);
    tracks = optimisticTracks;
    tracksVersion++;
    const optimisticVersion = tracksVersion;
    try {
      await reorderTracks(sessionId, orderedIds);
    } catch (err) {
      // Only revert if nothing else (e.g. a queue_reordered broadcast from
      // another member's concurrent reorder) has replaced `tracks` since we
      // applied our optimistic update — otherwise we'd clobber a legitimate
      // newer state with our stale snapshot.
      if (tracksVersion === optimisticVersion) {
        tracks = previousTracks;
        tracksVersion++;
      }
      throw err;
    }
  }

  async function handleRemove(track: Track) {
    const previousTracks = tracks;
    tracks = tracks.filter((t) => t.id !== track.id);
    tracksVersion++;
    const optimisticVersion = tracksVersion;
    try {
      await removeTrack(sessionId, track.id);
      if (nowPlaying?.id === track.id) {
        nowPlaying = null;
      }
    } catch (err) {
      // Same version-guard as handleReorder's revert — don't clobber a newer
      // broadcast-derived state (e.g. a track_removed event that already
      // arrived) with our stale pre-removal snapshot.
      if (tracksVersion === optimisticVersion) {
        tracks = previousTracks;
        tracksVersion++;
      }
      throw err;
    }
  }

  onDestroy(() => {
    ws?.close();
  });

  async function handleLeave() {
    await leaveSession(sessionId);
    goto('/');
  }

  function handleSend() {
    if (!ws || !message.trim()) return;
    // The server broadcasts to every connection in the session, including the
    // sender's own socket — `onMessage` renders it, so don't also push here.
    ws.send('message', { text: message.trim(), sender: displayName });
    message = '';
  }
</script>

{#if session}
  {#if sessionEnded}
    <p class="session-ended">This session has ended (it was idle too long). Start a new one from the home page.</p>
  {/if}

  <SessionCard
    code={session.code}
    participants={session.participants}
  />
  <p class="online">{session.online} online</p>

  <p class="status" class:connected>{connected ? 'Connected' : 'Disconnected'}</p>

  {#if messages.length}
    <div class="messages">
      {#each messages as msg}
        <div class="message">
          <strong>{msg.sender}:</strong> {msg.text}
        </div>
      {/each}
    </div>
  {/if}

  <form class="chat-form" onsubmit={(e) => { e.preventDefault(); handleSend(); }}>
    <input class="chat-input" bind:value={message} placeholder="Type a message..." />
    <button type="submit" class="btn btn-primary">Send</button>
  </form>

  <YoutubeDownloadForm onSubmit={handleSubmitTrack} />

  <QueueList
    {tracks}
    participants={session.participants}
    onReorder={handleReorder}
    onPlay={(t) => (nowPlaying = t)}
    onRemove={handleRemove}
  />

  {#if nowPlaying}
    <TrackPlayer {sessionId} track={nowPlaying} />
    <button class="btn btn-secondary" onclick={() => (nowPlaying = null)}>Stop</button>
  {/if}

  <button class="btn btn-secondary" onclick={handleLeave}>Leave Session</button>
{:else if loading}
  <p class="loading">Loading session...</p>
{/if}

<style>
  .online { color: #666; }

  .session-ended {
    color: #d32f2f;
    font-weight: 600;
    margin-bottom: 1rem;
  }

  .connected { color: #16a34a; }
  .status:not(.connected) { color: #d32f2f; }

  .messages {
    max-height: 300px;
    overflow-y: auto;
    margin: 1rem 0;
  }

  .message {
    padding: 0.25rem 0;
    border-bottom: 1px solid #eee;
  }

  form {
    display: flex;
    gap: 1rem;
    margin: 1.5rem 0;
  }

  input {
    flex: 1;
    padding: 0.5rem;
  }

  .btn {
    padding: 0.5rem 1.5rem;
    border: none;
    border-radius: 4px;
    cursor: pointer;
  }

  .loading {
    margin: 1rem;
  }

  .chat-form {
    display: flex;
    gap: 1rem;
    margin: 1.5rem 0;
  }

  .chat-input {
    flex: 1;
    padding: 0.5rem;
  }
</style>
