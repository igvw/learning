<script lang="ts">
  import type { RouteName } from '../lib/types';

  export let currentRoute: RouteName = 'quiz';
  export let onNavigate: (route: RouteName) => void = () => {};
  export let onToggleMenu: () => void = () => {};
</script>

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
  </nav>
</header>
