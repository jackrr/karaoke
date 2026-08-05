<div class="session-layout">
  <slot />
</div>

<style>
  :global(.session-layout) {
    display: flex;
    flex-direction: column;
    max-width: 960px;
    margin: 0 auto;
    padding: 2rem;
    min-width: 0;
  }
</style>