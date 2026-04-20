<script lang="ts">
  import type { AuthActor, RouteName } from '../lib/types';

  export let currentRoute: RouteName = 'quiz';
  export let currentActor: AuthActor | null = null;
  export let onNavigate: (route: RouteName) => void = () => {};
  export let onToggleMenu: () => void = () => {};
  export let onLogout: () => Promise<void> | void = () => {};
  export let importStatusVisible = false;
  export let importStatusLabel = '';
  export let importStatusDetail = '';
  export let importStatusTone: 'progress' | 'info' | 'error' = 'progress';
  export let onOpenImportStatus: () => void = () => {};

  let userMenuOpen = false;

  function userInitial(actor: AuthActor | null): string {
    const value = actor?.display_name?.trim() || actor?.handle?.trim() || '';
    return value ? value[0].toUpperCase() : '?';
  }

  function actorBadgeStyle(actor: AuthActor | null): string {
    if (!actor) {
      return '--user-badge-bg: rgba(115, 115, 125, 0.28); --user-badge-border: rgba(161, 161, 170, 0.34); --user-badge-text: #e4e4e7;';
    }

    const seed = `${actor.handle}:${actor.role}:${actor.display_name}`;
    let hash = 0;
    for (let index = 0; index < seed.length; index += 1) {
      hash = (hash * 31 + seed.charCodeAt(index)) % 360;
    }
    return `--user-badge-bg: hsla(${hash}, 72%, 52%, 0.28); --user-badge-border: hsla(${hash}, 86%, 70%, 0.44); --user-badge-text: hsl(${hash}, 95%, 92%);`;
  }

  async function handleLogout(): Promise<void> {
    userMenuOpen = false;
    await onLogout();
  }

  $: manageLabel = currentActor?.role === 'admin' ? 'Admin' : 'Manage';
  $: displayedActor = currentActor;
</script>

<svelte:window
  on:click={() => (userMenuOpen = false)}
  on:keydown={(event) => {
    if (event.key === 'Escape') {
      userMenuOpen = false;
    }
  }}
/>

<header class="app-header">
  <div class="header-brand">
    <button class="menu-toggle" type="button" on:click={onToggleMenu} aria-label="Open module menu">
      <span></span>
      <span></span>
      <span></span>
    </button>
    <div>
      <h1>Learning</h1>
    </div>
  </div>

  <nav class="main-nav" aria-label="Primary">
    <button type="button" class:active={currentRoute === 'quiz'} on:click={() => onNavigate('quiz')}>
      Quiz
    </button>
    <button type="button" class:active={currentRoute === 'stats'} on:click={() => onNavigate('stats')}>
      Stats
    </button>
    <button type="button" class:active={currentRoute === 'admin'} on:click={() => onNavigate('admin')}>
      {manageLabel}
    </button>
  </nav>

  <div class="header-user-tools">
    {#if importStatusVisible}
      <button
        type="button"
        class={`header-import-status tone-${importStatusTone}`}
        title={importStatusDetail || importStatusLabel}
        on:click={onOpenImportStatus}
      >
        <span class="header-import-status-indicator" aria-hidden="true"></span>
        <span>{importStatusLabel}</span>
      </button>
    {/if}

    <div class="user-menu-shell">
      <button
        type="button"
        class="user-avatar user-avatar-button"
        style={actorBadgeStyle(displayedActor)}
        aria-haspopup="menu"
        aria-expanded={userMenuOpen}
        aria-label={displayedActor ? `Open user menu for ${displayedActor.display_name}` : 'Open account menu'}
        on:click|stopPropagation={() => (userMenuOpen = !userMenuOpen)}
      >
        {userInitial(displayedActor)}
      </button>

      {#if userMenuOpen && displayedActor}
        <div class="user-menu" role="menu" aria-label="Account menu" tabindex="-1">
          <p class="user-menu-title">{displayedActor.display_name}</p>
          <p class="user-menu-empty">
            {displayedActor.role}{displayedActor.is_demo ? ' account (ephemeral demo)' : ' account'}
          </p>
          <button type="button" class="user-menu-item" role="menuitem" on:click={() => void handleLogout()}>
            <span>Log out</span>
          </button>
        </div>
      {/if}
    </div>
  </div>
</header>
