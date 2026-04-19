<script lang="ts">
  export let bootstrapRequired = false;
  export let busy = false;
  export let errorMessage = '';
  export let onLogin: (payload: { handle: string; password: string }) => Promise<void> = async () => {};
  export let onBootstrapAdmin: (payload: {
    handle: string;
    display_name: string;
    password: string;
  }) => Promise<void> = async () => {};
  export let onDemo: () => Promise<void> = async () => {};

  let handle = '';
  let password = '';
  let bootstrapHandle = '';
  let bootstrapDisplayName = '';
  let bootstrapPassword = '';
  let bootstrapPasswordConfirm = '';

  async function handleLoginSubmit(): Promise<void> {
    await onLogin({ handle: handle.trim(), password });
  }

  async function handleBootstrapSubmit(): Promise<void> {
    await onBootstrapAdmin({
      handle: bootstrapHandle.trim(),
      display_name: bootstrapDisplayName.trim(),
      password: bootstrapPassword
    });
  }

  $: bootstrapPasswordsMatch = bootstrapPassword === bootstrapPasswordConfirm;
  $: bootstrapReady = Boolean(
    bootstrapHandle.trim() &&
      bootstrapDisplayName.trim() &&
      bootstrapPassword &&
      bootstrapPasswordConfirm &&
      bootstrapPasswordsMatch
  );
</script>

<section class="page auth-page">
  <div class="panel auth-panel">
    <div class="page-intro">
      <div>
        <h2>{bootstrapRequired ? 'Create the first admin account' : 'Sign in'}</h2>
        {#if bootstrapRequired}
          <p class="muted-copy">Create the first admin account to unlock the app.</p>
        {/if}
      </div>
    </div>

    {#if errorMessage}
      <div class="banner error">{errorMessage}</div>
    {/if}

    <div class="admin-stack">
      {#if bootstrapRequired}
        <article class="panel admin-bar-panel">
          <div class="panel-header">
            <div><h3>Create admin account</h3></div>
          </div>
          <div class="admin-bar-form user-bar-form">
            <label class="field">
              <span>Username</span>
              <input type="text" bind:value={bootstrapHandle} placeholder="admin" />
            </label>
            <label class="field">
              <span>Display name</span>
              <input type="text" bind:value={bootstrapDisplayName} placeholder="Admin" />
            </label>
            <label class="field">
              <span>Password</span>
              <input type="password" bind:value={bootstrapPassword} placeholder="At least 8 characters" />
            </label>
            <label class="field">
              <span>Confirm password</span>
              <input type="password" bind:value={bootstrapPasswordConfirm} placeholder="Repeat the password" />
            </label>
            <div class="admin-action-slot">
              <button class="primary-button" type="button" disabled={busy || !bootstrapReady} on:click={() => void handleBootstrapSubmit()}>
                {busy ? 'Creating...' : 'Create Admin'}
              </button>
            </div>
          </div>
          {#if bootstrapPasswordConfirm && !bootstrapPasswordsMatch}
            <p class="muted-copy">Passwords must match before creating the first admin.</p>
          {/if}
        </article>
      {:else}
        <article class="panel admin-bar-panel">
          <form class="admin-bar-form user-bar-form" on:submit|preventDefault={() => void handleLoginSubmit()}>
            <label class="field">
              <span class="sr-only">Username</span>
              <input type="text" bind:value={handle} placeholder="Username" />
            </label>
            <label class="field">
              <span class="sr-only">Password</span>
              <input type="password" bind:value={password} placeholder="Password" />
            </label>
            <div class="admin-action-slot">
              <div class="auth-action-row">
                <button class="primary-button" type="submit" disabled={busy}>
                  {busy ? 'Signing in...' : 'Sign In'}
                </button>
                <button class="review-button" type="button" disabled={busy} on:click={() => void onDemo()}>
                  {busy ? 'Opening demo...' : 'Demo'}
                </button>
              </div>
            </div>
          </form>
        </article>
      {/if}
    </div>
  </div>
</section>
