<script>
  import '../app.css';
</script>

<div class="hero">
  <h1>Karaoke</h1>
  <p class="subtitle">Create or join a session to start singing</p>

  <div class="actions">
    <button class="btn btn-primary" on:click={() => alert('Create session coming soon!')}>
      Create Session
    </button>
    <button class="btn btn-secondary" on:click={() => alert('Join session coming soon!')}>
      Join Session
    </button>
  </div>
</div>

<style>
  .hero {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 1.5rem;
    padding-top: 4rem;
  }

  .subtitle {
    color: #666;
    font-size: 1.1rem;
  }

  .actions {
    display: flex;
    gap: 1rem;
  }

  .btn {
    display: inline-block;
    padding: 0.6rem 1.5rem;
    border: none;
    border-radius: 6px;
    font-size: 1rem;
    cursor: pointer;
    transition: opacity 0.15s;
  }

  .btn:hover {
    opacity: 0.85;
  }

  .btn-primary {
    background: #1a1a1a;
    color: #fff;
  }

  .btn-secondary {
    background: #e2e2e2;
    color: #1a1a1a;
  }
</style>
