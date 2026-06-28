<script lang="ts">
  import { get } from 'svelte/store';
  import { currentTrack, connectionState, session } from '$lib/store';
  import ReconnectBanner from '$lib/components/ReconnectBanner.svelte';
  import NowPlayingBar from '$lib/components/NowPlayingBar.svelte';
  import '../app.css';
</script>

<svelte:head>
  <title>Karaoke</title>
</svelte:head>

<div class="app">
  <ReconnectBanner {connectionState} />
  <NowPlayingBar />
  <main class="content">
    <slot />
  </main>
</div>

<style>
  .app {
    display: flex;
    flex-direction: column;
    min-height: 100vh;
  }
  .content {
    flex: 1;
    padding: 16px;
    max-width: 960px;
    margin: 0 auto;
    width: 100%;
  }
</style>
