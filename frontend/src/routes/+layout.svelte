<style>
  .navbar {
    display: flex;
    align-items: center;
    gap: 1rem;
    padding: 1rem 2rem;
    background: #fff;
    border-bottom: 1px solid #e2e2e2;
  }

  .navbar > a:hover {
    text-decoration: underline;
  }

  main {
    padding: 2rem;
    max-width: 960px;
    margin: 0 auto;
  }
</style>

<nav class="navbar">
  <a href="/">Karaoke</a>
</nav>

<main>
  <slot />
</main>
