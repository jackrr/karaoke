<script lang="ts">
  import type { LrcLine } from '../utils/lrc';
  import { findCurrentLineIndex } from '../utils/lrc';
  import { fly } from 'svelte/transition';
  import { cubicOut } from 'svelte/easing';

  let { lines, currentTime }: { lines: LrcLine[]; currentTime: number } = $props();
  const activeIndex = $derived(findCurrentLineIndex(lines, currentTime));

  // Buffer offsets stay in the DOM (invisible) so they can slide into place
  // instead of popping in, then fly in/out only crosses the buffer's edge.
  const RADIUS = 2;
  const visibleLines = $derived(
    lines
      .map((line, index) => ({ line, offset: index - activeIndex }))
      .filter(({ offset }) => Math.abs(offset) <= RADIUS)
  );
</script>

<div class="lyrics">
  {#if activeIndex === -1}
    <p class="line current" style="--offset: 0">♪</p>
  {/if}
  {#each visibleLines as { line, offset } (line.time)}
    <p
      class="line"
      class:current={offset === 0}
      class:adjacent={Math.abs(offset) === 1}
      class:far={Math.abs(offset) >= 2}
      style="--offset: {offset}"
      in:fly={{ y: offset > 0 ? 24 : -24, duration: 400, easing: cubicOut }}
      out:fly={{ y: offset > 0 ? 24 : -24, duration: 400, easing: cubicOut }}
    >
      {line.text}
    </p>
  {/each}
</div>

<style>
  .lyrics {
    position: relative;
    width: 100%;
    height: 9.5rem;
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .line {
    position: absolute;
    left: 0;
    right: 0;
    margin: 0;
    text-align: center;
    transform: translateY(calc(var(--offset) * 3.25rem));
    transition:
      transform 400ms cubic-bezier(0.33, 1, 0.68, 1),
      font-size 400ms cubic-bezier(0.33, 1, 0.68, 1),
      opacity 400ms cubic-bezier(0.33, 1, 0.68, 1);
  }

  .line.current {
    font-size: clamp(1.25rem, 5vw, 2.5rem);
    font-weight: 600;
    opacity: 1;
  }

  .line.adjacent {
    font-size: clamp(1rem, 4vw, 1.75rem);
    font-weight: 400;
    opacity: 0.4;
  }

  .line.far {
    font-size: clamp(1rem, 4vw, 1.75rem);
    font-weight: 400;
    opacity: 0;
  }
</style>
