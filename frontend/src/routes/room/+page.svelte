<script lang="ts">
  import { onMount, onDestroy } from 'svelte';
  import {
    session, queue, currentTrack, clients, connectionState, role
  } from '$lib/store';
  import { setup as setupWebSocket } from '$lib/hooks/useWebSocket.svelte';

  import PasscodeDisplay from '$lib/components/PasscodeDisplay.svelte';
  import ReconnectBanner from '$lib/components/ReconnectBanner.svelte';
  import NowPlayingBar   from '$lib/components/NowPlayingBar.svelte';
  import QueueList       from '$lib/components/QueueList.svelte';
  import PlayBackView    from '$lib/components/PlaybackView.svelte';
  import EnqueueMenu     from '$lib/components/EnqueueMenu.svelte';
  import LyricDisplay    from '$lib/components/LyricDisplay.svelte';

  let ws: ReturnType<ReturnType<typeof setupWebSocket>> | null = null;
  let wsId = crypto.randomUUID();

  function handleEnqueue(url: string, source: 'youtube' | 'upload') {
    ws?.send({
      type: 'enqueue',
      payload: {
        client_id: wsId,
        source,
        metadata: { title: url, source_url: url },
      },
    });
  }

  $: isHost = $role === 'host';
  $: ready  = !!$session;

  onMount(() => { if ($session) ws = setupWebSocket(crypto.randomUUID()).connect(); });
  onDestroy(()  => { ws?.disconnect(); });

  function leaveRoom() {
    ws?.disconnect();
    $session   = null;
    $queue     = [];
    $currentTrack = null;
    $role      = null;
    $connectionState = 'idle';
  }
</script>

<div class="room">
  {#if ready}
    <header class="room-header">
      <h2 class="room-title">Room {($session)?.passcode ?? ''}</h2>
      <span class={`role-badge {$role ?? ''}`}>{isHost ? 'Host' : 'Guest'}</span>
      <button class="btn-leave" on:click={leaveRoom}>Leave</button>
    </header>
    <div class="room-layout">
      <div class="panel-left">
        <EnqueueMenu onEnqueue={handleEnqueue} />
        <QueueList items={$queue} isHost={isHost} />
      </div>
      <main class="panel-center">
        <PlayBackView />
      </main>
      <aside class="panel-right">
        <div class="clients card">
          <h3>Connected ({($clients)?.length ?? 0})</h3>
          {@if !($clients)?.length}
            <p class="empty">No one else yet</p>
          {:else}
            <ul class="client-list">
              {#each $clients as c (c.client_id)}
                <li class="client-item">
                  <span class="status-dot {c.connected ? 'on' : 'off'}" />
                  <span class="client-type">{c.client_type}</span>
                </li>
              {/each}
            </ul>
          {/if}
        </div>
        <LyricDisplay mode="timed" />
      </aside>
    </div>
  {:else}
    <p class="empty">Loading room…</p>
  {/if}
</div>

<style>
  .room { display: flex; flex-direction: column; height: 100%; }
  .room-header {
    display: flex; align-items: center; gap: 12px;
    padding: 8px 0 12px; border-bottom: 1px solid var(--border);
  }
  .room-title { font-size: 1rem; margin: 0; }
  .role-badge {
    padding: 2px 10px; border-radius: 999px; font-size: 0.75rem; font-weight: 600;
  }
  .role-badge.host   { background: #7c3aed40; color: #a78bfa; }
  .role-badge.guest  { background: var(--bg-tertiary); color: var(--text-secondary); }
  .btn-leave {
    margin-left: auto; background: transparent; border: 1px solid var(--border);
    color: var(--text-muted); padding: 4px 12px; border-radius: var(--radius-sm);
    cursor: pointer; font-size: 0.8rem;
  }
  .btn-leave:hover { border-color: var(--accent); color: var(--accent); }
  .room-layout {
    display: grid; grid-template-columns: 1fr 1.2fr 220px;
    gap: 16px; flex: 1; margin-top: 12px;
  }
  .panel-left, .panel-right { overflow-y: auto; }
  .panel-left { display: flex; flex-direction: column; gap: 12px; }
  .clients { margin-top: 12px; }
  .client-list { list-style: none; padding: 0; }
  .client-item { display: flex; align-items: center; gap: 8px; padding: 6px 8px; }
  .status-dot { width: 8px; height: 8px; border-radius: 50%; background: var(--text-muted); }
  .status-dot.on   { background: var(--success); }
  .client-type { font-size: 0.85rem; color: var(--text-secondary); }
  .empty { text-align: center; color: var(--text-muted); margin: 16px 0; }
</style>
