<script lang="ts">
  import type { User } from '../../lib/types';

  export let users: User[] = [];
  export let isDemo = false;
  export let showHeading = true;
  export let onCreateUser: (payload: {
    handle: string;
    display_name: string;
    role: 'admin' | 'user';
    password: string;
  }) => Promise<User> = async () => {
    throw new Error('User creation handler is not configured.');
  };
  export let onUpdateUserRole: (userId: number, role: 'admin' | 'user') => Promise<User> = async () => {
    throw new Error('User role update handler is not configured.');
  };
  export let onUpdateUserPassword: (userId: number, password: string) => Promise<void> = async () => {
    throw new Error('Password update handler is not configured.');
  };

  let userHandle = '';
  let userDisplayName = '';
  let userPassword = '';
  let userPasswordConfirm = '';
  let userRole: 'admin' | 'user' = 'user';
  let userSaving = false;
  let userError = '';
  let userSuccess = '';
  let managedUserId = '';
  let managedUserRole: 'admin' | 'user' = 'user';
  let managingUserSignature = '';
  let roleUpdateBusy = false;
  let roleUpdateError = '';
  let roleUpdateSuccess = '';
  let passwordResetValue = '';
  let passwordResetConfirm = '';
  let passwordResetBusy = false;
  let passwordResetError = '';
  let passwordResetSuccess = '';

  async function handleCreateUser(): Promise<void> {
    userError = '';
    userSuccess = '';
    userSaving = true;
    try {
      const created = await onCreateUser({
        handle: userHandle.trim(),
        display_name: userDisplayName.trim(),
        role: userRole,
        password: userPassword
      });
      userSuccess = `Account ready: ${created.display_name}.`;
      userHandle = '';
      userDisplayName = '';
      userPassword = '';
      userPasswordConfirm = '';
      userRole = 'user';
    } catch (error) {
      userError = error instanceof Error ? error.message : 'Unable to create this account.';
    } finally {
      userSaving = false;
    }
  }

  async function handleUpdateRole(): Promise<void> {
    roleUpdateError = '';
    roleUpdateSuccess = '';
    roleUpdateBusy = true;
    try {
      if (!selectedManagedUser) {
        throw new Error('Select an account before changing its role.');
      }
      const updated = await onUpdateUserRole(Number(managedUserId), managedUserRole);
      roleUpdateSuccess = `Role updated for ${updated.display_name}.`;
    } catch (error) {
      roleUpdateError = error instanceof Error ? error.message : 'Unable to update this role.';
    } finally {
      roleUpdateBusy = false;
    }
  }

  async function handleResetPassword(): Promise<void> {
    passwordResetError = '';
    passwordResetSuccess = '';
    passwordResetBusy = true;
    try {
      if (!selectedManagedUser) {
        throw new Error('Select an account before updating its password.');
      }
      await onUpdateUserPassword(Number(managedUserId), passwordResetValue);
      passwordResetSuccess = 'Password updated.';
      passwordResetValue = '';
      passwordResetConfirm = '';
    } catch (error) {
      passwordResetError = error instanceof Error ? error.message : 'Unable to update this password.';
    } finally {
      passwordResetBusy = false;
    }
  }

  $: selectedManagedUser = users.find((user) => user.id === Number(managedUserId)) ?? null;
  $: createPasswordsMatch = userPassword === userPasswordConfirm;
  $: resetPasswordsMatch = passwordResetValue === passwordResetConfirm;
  $: canCreateUser = Boolean(
    !isDemo &&
      !userSaving &&
      userHandle.trim() &&
      userDisplayName.trim() &&
      userPassword &&
      userPasswordConfirm &&
      createPasswordsMatch
  );
  $: canUpdateRole = Boolean(
    !isDemo &&
      !roleUpdateBusy &&
      selectedManagedUser &&
      managedUserRole !== selectedManagedUser.role
  );
  $: canResetPassword = Boolean(
    !isDemo &&
      !passwordResetBusy &&
      selectedManagedUser &&
      passwordResetValue &&
      passwordResetConfirm &&
      resetPasswordsMatch
  );
  $: if (users.length > 0 && !users.some((user) => user.id === Number(managedUserId))) {
    managedUserId = String(users[0].id);
  }
  $: if (users.length === 0) {
    managedUserId = '';
  }
  $: {
    const nextManagedSignature = selectedManagedUser ? `${selectedManagedUser.id}:${selectedManagedUser.role}` : '';
    if (nextManagedSignature !== managingUserSignature) {
      managingUserSignature = nextManagedSignature;
      managedUserRole = selectedManagedUser?.role === 'admin' ? 'admin' : 'user';
      roleUpdateError = '';
      roleUpdateSuccess = '';
      passwordResetError = '';
      passwordResetSuccess = '';
    }
  }
</script>

<article class="panel admin-bar-panel">
  {#if showHeading}
    <div class="panel-header">
      <div><h3>Accounts</h3></div>
    </div>
  {/if}

  {#if userError}
    <div class="banner error">{userError}</div>
  {/if}
  {#if userSuccess}
    <div class="banner success">{userSuccess}</div>
  {/if}

  <div class="admin-bar-form user-bar-form">
    <label class="field">
      <span>Username</span>
      <input type="text" bind:value={userHandle} placeholder="new-username" />
    </label>
    <label class="field">
      <span>Display name</span>
      <input type="text" bind:value={userDisplayName} placeholder="Ignazio" />
    </label>
    <label class="field">
      <span>Role</span>
      <select bind:value={userRole}>
        <option value="user">User</option>
        <option value="admin">Admin</option>
      </select>
    </label>
    <label class="field">
      <span>Password</span>
      <input type="password" bind:value={userPassword} placeholder="At least 8 characters" />
    </label>
    <label class="field">
      <span>Confirm password</span>
      <input type="password" bind:value={userPasswordConfirm} placeholder="Repeat the password" />
    </label>
    <div class="admin-action-slot">
      <button class="primary-button" type="button" disabled={!canCreateUser} on:click={() => void handleCreateUser()}>
        {userSaving ? 'Creating...' : 'Create Account'}
      </button>
    </div>
  </div>
  {#if userPasswordConfirm && !createPasswordsMatch}
    <p class="muted-copy">Passwords must match before creating an account.</p>
  {/if}

  <div class="admin-bar-form user-bar-form">
    <label class="field">
      <span>Manage account</span>
      <select bind:value={managedUserId}>
        <option value="">Select account</option>
        {#each users as user}
          <option value={user.id}>{user.display_name} ({user.role})</option>
        {/each}
      </select>
    </label>
    <label class="field">
      <span>Role</span>
      <select bind:value={managedUserRole} disabled={!selectedManagedUser || roleUpdateBusy}>
        <option value="user">User</option>
        <option value="admin">Admin</option>
      </select>
    </label>
    <div class="admin-action-slot">
      <button class="primary-button" type="button" disabled={!canUpdateRole} on:click={() => void handleUpdateRole()}>
        {roleUpdateBusy ? 'Saving...' : 'Save Role'}
      </button>
    </div>
  </div>
  {#if roleUpdateError}
    <p class="muted-copy">{roleUpdateError}</p>
  {/if}
  {#if roleUpdateSuccess}
    <p class="muted-copy">{roleUpdateSuccess}</p>
  {/if}

  <div class="admin-bar-form user-bar-form">
    <label class="field">
      <span>New password</span>
      <input type="password" bind:value={passwordResetValue} placeholder="At least 8 characters" />
    </label>
    <label class="field">
      <span>Confirm password</span>
      <input type="password" bind:value={passwordResetConfirm} placeholder="Repeat the password" />
    </label>
    <div class="admin-action-slot">
      <button class="primary-button" type="button" disabled={!canResetPassword} on:click={() => void handleResetPassword()}>
        {passwordResetBusy ? 'Saving...' : 'Update Password'}
      </button>
    </div>
  </div>
  {#if passwordResetConfirm && !resetPasswordsMatch}
    <p class="muted-copy">Passwords must match before updating a password.</p>
  {/if}
  {#if passwordResetError}
    <p class="muted-copy">{passwordResetError}</p>
  {/if}
  {#if passwordResetSuccess}
    <p class="muted-copy">{passwordResetSuccess}</p>
  {/if}
</article>
