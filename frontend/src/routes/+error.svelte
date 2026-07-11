<script>
  import { page } from '$app/stores';
</script>

<svelte:head>
  <title>{$page.status} — {$page.error?.message ?? 'Error'}</title>
</svelte:head>

<div class="error">
  <h1>{$page.status} — {$page.error?.message ?? 'Something went wrong'}</h1>
  <a href="/">Go home</a>
</div>

<style>
  .error {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 1.5rem;
    padding-top: 6rem;
  }

  .error a {
    color: #1a1a1a;
    text-decoration: underline;
  }
</style>
