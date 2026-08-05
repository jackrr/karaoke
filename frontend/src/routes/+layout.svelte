<script>
  import '../app.css';
</script>

<style>
  .navbar {
    display: flex;
    align-items: center;
    gap: 1rem;
    padding: 1rem 2rem;
    background: var(--color-surface);
    border-bottom: 1px solid var(--color-border);
  }

  .navbar > a:hover {
    text-decoration: underline;
  }

  main {
    padding: 2rem;
    max-width: 960px;
    margin: 0 auto;
    min-width: 0;
  }
</style>

<nav class="navbar">
  <a href="/">Karaoke</a>
</nav>

<main>
  <slot />
</main>
