<script lang="ts">
  import type { RouteName, User } from '../lib/types';

  export let currentRoute: RouteName = 'quiz';
  export let users: User[] = [];
  export let activeUserId: number | null = null;
  export let onNavigate: (route: RouteName) => void = () => {};
  export let onToggleMenu: () => void = () => {};
  export let onSelectUser: (userId: number) => void = () => {};
  let userMenuOpen = false;

  function activeUser(usersList: User[], userId: number | null): User | null {
    if (userId === null) {
      return null;
    }
    return usersList.find((user) => user.id === userId) ?? null;
  }

  function userInitial(user: User | null): string {
    const value = user?.display_name?.trim() || user?.handle?.trim() || '';
    return value ? value[0].toUpperCase() : '?';
  }

  function userBadgeStyle(user: User | null): string {
    if (!user) {
      return '--user-badge-bg: rgba(115, 115, 125, 0.28); --user-badge-border: rgba(161, 161, 170, 0.34); --user-badge-text: #e4e4e7;';
    }

    const seed = `${user.id}:${user.handle}:${user.display_name}`;
    let hash = 0;
    for (let index = 0; index < seed.length; index += 1) {
      hash = (hash * 31 + seed.charCodeAt(index)) % 360;
    }
    const hue = hash;
    return `--user-badge-bg: hsla(${hue}, 72%, 52%, 0.28); --user-badge-border: hsla(${hue}, 86%, 70%, 0.44); --user-badge-text: hsl(${hue}, 95%, 92%);`;
  }

  function handleSelectUser(userId: number): void {
    onSelectUser(userId);
    userMenuOpen = false;
  }

  $: selectedUser = activeUser(users, activeUserId);
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
      <p class="eyebrow">Keyboard-first learning</p>
      <h1>Learning App</h1>
    </div>
  </div>

  <nav class="main-nav" aria-label="Primary">
    <button
      type="button"
      class:active={currentRoute === 'quiz'}
      on:click={() => onNavigate('quiz')}
    >
      Quiz
    </button>
    <button
      type="button"
      class:active={currentRoute === 'stats'}
      on:click={() => onNavigate('stats')}
    >
      Stats
    </button>
    <button
      type="button"
      class:active={currentRoute === 'admin'}
      on:click={() => onNavigate('admin')}
    >
      Admin
    </button>
  </nav>

  <div class="header-user-tools">
    <div class="user-menu-shell">
      <button
        type="button"
        class="user-avatar user-avatar-button"
        style={userBadgeStyle(selectedUser)}
        aria-haspopup="menu"
        aria-expanded={userMenuOpen}
        aria-label={selectedUser ? `Open user menu for ${selectedUser.display_name}` : 'Open user menu'}
        title={selectedUser ? selectedUser.display_name : 'No active user'}
        on:click|stopPropagation={() => (userMenuOpen = !userMenuOpen)}
      >
        {userInitial(selectedUser)}
      </button>

      {#if userMenuOpen}
        <div class="user-menu" role="menu" aria-label="User menu" tabindex="-1">
          {#if users.length > 0}
            <p class="user-menu-title">Switch user</p>
            {#each users as user (user.id)}
              <button
                type="button"
                class="user-menu-item"
                class:active={user.id === activeUserId}
                role="menuitemradio"
                aria-checked={user.id === activeUserId}
                on:click={() => handleSelectUser(user.id)}
              >
                <span>{user.display_name}</span>
                {#if user.id === activeUserId}
                  <span class="user-menu-item-state">Current</span>
                {/if}
              </button>
            {/each}
          {:else}
            <p class="user-menu-empty">Create a user in Admin.</p>
          {/if}
        </div>
      {/if}
    </div>
  </div>
</header>
