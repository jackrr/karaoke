<nav class="session-layout">
  <a href="/">← Home</a>
  <slot />
</nav>

<style>
  :global(.session-layout) {
    display: flex;
    flex-direction: column;
    max-width: 960px;
    margin: 0 auto;
    padding: 2rem;
  }

  :global(.session-layout a) {
    color: #333;
    text-decoration: none;
    margin-bottom: 1rem;
  }
</style>