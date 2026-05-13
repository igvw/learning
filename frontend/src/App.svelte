<script lang="ts">
  import { onMount } from 'svelte';
  import AdminPage from './components/AdminPage.svelte';
  import AuthPage from './components/AuthPage.svelte';
  import EditorDrawer from './components/EditorDrawer.svelte';
  import Header from './components/Header.svelte';
  import ImportDrawer from './components/ImportDrawer.svelte';
  import ModuleMenu from './components/ModuleMenu.svelte';
  import QuizPage from './components/QuizPage.svelte';
  import StatsPage from './components/StatsPage.svelte';
  import { buildModerationRevisionSeed } from './lib/moderation-editor';
  import {
    findModuleTitle,
    persistSelectedModule as persistSelectedModuleSelection,
    routeFromPath
  } from './lib/app-state';
  import {
    loadRoleDataForActor,
    loadStatsForActor,
    pathForRoute,
    refreshAuthenticatedShellData,
    resolveAuthSessionState,
    type RefreshedShellState
  } from './lib/app-shell-data';
  import {
    closeImportUiState,
    initialImportUiState,
    openImportUiForModule,
    resetImportUiState,
    updateImportUiDraft
  } from './lib/app-shell-import';
  import { commitImportUiFlow, startImportUiFlow } from './lib/app-shell-import-actions';
  import { IMPORT_COMMIT_CHUNK_SIZE } from './lib/import-session';
  import { runBulkModeration, saveQuestionMutation } from './lib/app-shell-mutations';
  import {
    bootstrapAdmin,
    commitQuestionImport,
    createModule,
    createQuestion,
    createQuizSession,
    createUser,
    deleteModule,
    deleteQuestion,
    deleteRejectedModule,
    exportContentArchive,
    getCurrentActor,
    getHealth,
    getModerationQueue,
    getModulesTree,
    getMyContributions,
    getQuestion,
    getStats,
    getUsers,
    login,
    logout,
    reviewModule,
    reviewQuestion,
    reviewQuestionRevision,
    reviseQuestion,
    submitQuizAnswer,
    updateModule,
    updateUserPassword,
    updateUserRole,
    validateQuestionImportRows,
    validateQuestionImportText,
    withdrawQuestionRevision
  } from './lib/api';
  import { ensureModulePath, findModuleNode as findModuleNodeInTree } from './lib/module-paths';
  import { applySubmitAnswerResult } from './lib/quiz-session';
  import type {
    AuthActor,
    BulkModerationResult,
    CreateModulePayload,
    CreateUserPayload,
    HealthResponse,
    ModerationActionPayload,
    ModerationKind,
    ModerationQueue,
    ModerationRevisionActionPayload,
    ModuleNode,
    MyContributions,
    QuestionDraftPayload,
    QuestionImportRowPayload,
    QuestionRevisionProposal,
    QuestionRow,
    QuizSession,
    RouteName,
    StatsResponse,
    UpdateModulePayload,
    User
  } from './lib/types';

  let currentRoute: RouteName = 'quiz';
  let modules: ModuleNode[] = [];
  let selectedModuleId: number | null = null;
  let moduleMenuOpen = false;

  let currentActor: AuthActor | null = null;
  let users: User[] = [];
  let moderationQueue: ModerationQueue | null = null;
  let contributions: MyContributions | null = null;
  let health: HealthResponse | null = null;
  let authLoading = true;
  let authBusy = false;
  let authError = '';

  let session: QuizSession | null = null;
  let quizBusyItemId: number | null = null;
  let openingQuizEditorQuestionId: number | null = null;
  let quizError = '';
  let quizQuestionCount = 10;

  let stats: StatsResponse | null = null;
  let statsLoading = false;
  let statsError = '';
  let reviewOnly = false;

  let editorOpen = false;
  let editorMode: 'standard' | 'moderation' = 'standard';
  let editorOrigin: 'default' | 'quiz' = 'default';
  let editingQuestion: QuestionRow | null = null;
  let editingRevisionProposal: QuestionRevisionProposal | null = null;
  let savingQuestion = false;
  let deletingQuestion = false;
  let withdrawingRevisionQuestionId: number | null = null;

  let importState = initialImportUiState();
  let instanceKey = 'default';

  function persistSelectedModule(moduleId: number | null): void {
    persistSelectedModuleSelection(window.localStorage, {
      instanceKey,
      modules,
      moduleId
    });
  }

  function applySelectedModule(moduleId: number | null): void {
    selectedModuleId = moduleId;
    persistSelectedModule(moduleId);
  }

  function resetAuthenticatedState(): void {
    modules = [];
    selectedModuleId = null;
    session = null;
    stats = null;
    statsError = '';
    openingQuizEditorQuestionId = null;
    users = [];
    moderationQueue = null;
    contributions = null;
    reviewOnly = false;
    moduleMenuOpen = false;
    importState = resetImportUiState(importState, true);
  }

  function closeImportDrawer(): void {
    importState = closeImportUiState(importState);
  }

  function updateImportDraft(qmlText: string, rows: QuestionImportRowPayload[]): void {
    importState = updateImportUiDraft(importState, qmlText, rows);
  }

  async function loadRoleData(): Promise<void> {
    const roleData = await loadRoleDataForActor({
      actor: currentActor,
      getUsers,
      getModerationQueue,
      getMyContributions
    });
    users = roleData.users;
    moderationQueue = roleData.moderationQueue;
    contributions = roleData.contributions;
  }

  function applyRefreshedShellData(refreshed: RefreshedShellState): void {
    modules = refreshed.modules;
    importState = {
      ...importState,
      targetModuleId: refreshed.importTargetModuleId
    };
    applySelectedModule(refreshed.selectedModuleId);
    users = refreshed.users;
    moderationQueue = refreshed.moderationQueue;
    contributions = refreshed.contributions;
    if (currentRoute === 'stats') {
      stats = refreshed.stats;
      statsError = refreshed.statsErrorMessage;
    }
  }

  async function refreshAuthenticatedData(actor: AuthActor | null = currentActor): Promise<void> {
    const refreshed = await refreshAuthenticatedShellData({
      actor,
      currentRoute,
      selectedModuleId,
      importState,
      instanceKey,
      storage: window.localStorage,
      getModulesTree,
      getUsers,
      getModerationQueue,
      getMyContributions,
      getStats
    });
    applyRefreshedShellData(refreshed);
  }

  async function loadStats(): Promise<void> {
    statsLoading = true;
    const loadedStats = await loadStatsForActor({
      actor: currentActor,
      selectedModuleId,
      getStats
    });
    stats = loadedStats.stats;
    statsError = loadedStats.errorMessage;
    statsLoading = false;
  }

  async function resolveAuthSession(): Promise<void> {
    authLoading = true;
    authError = '';
    const resolvedState = await resolveAuthSessionState({
      currentRoute,
      selectedModuleId,
      importState,
      storage: window.localStorage,
      getHealth,
      getCurrentActor,
      getModulesTree,
      getUsers,
      getModerationQueue,
      getMyContributions,
      getStats
    });
    health = resolvedState.health;
    instanceKey = resolvedState.instanceKey;
    currentActor = resolvedState.currentActor;

    if (!resolvedState.currentActor) {
      resetAuthenticatedState();
      authLoading = false;
      return;
    }

    applyRefreshedShellData(resolvedState);
    authLoading = false;
  }

  async function navigate(route: RouteName): Promise<void> {
    currentRoute = route;
    window.history.pushState({}, '', pathForRoute(route));
    if (route === 'stats') {
      await loadStats();
    }
    if (route === 'admin' && currentActor) {
      await loadRoleData();
    }
  }

  async function handleSelectModule(moduleId: number | null, keepMenuOpen = false): Promise<void> {
    const moduleChanged = selectedModuleId !== moduleId;
    applySelectedModule(moduleId);
    moduleMenuOpen = keepMenuOpen;
    if (!moduleChanged) {
      return;
    }
    session = null;
    quizError = '';
    if (currentRoute === 'stats') {
      await loadStats();
    }
  }

  async function handleLogin(payload: { handle: string; password: string }): Promise<void> {
    authBusy = true;
    authError = '';
    try {
      currentActor = await login(payload);
      await refreshAuthenticatedData(currentActor);
    } catch (error) {
      authError = error instanceof Error ? error.message : 'Unable to sign in.';
    } finally {
      authBusy = false;
    }
  }

  async function handleBootstrapAdmin(payload: {
    handle: string;
    display_name: string;
    password: string;
  }): Promise<void> {
    authBusy = true;
    authError = '';
    try {
      currentActor = await bootstrapAdmin(payload);
      health = health ? { ...health, bootstrap_required: false } : null;
      await refreshAuthenticatedData(currentActor);
    } catch (error) {
      authError = error instanceof Error ? error.message : 'Unable to create the first admin.';
    } finally {
      authBusy = false;
    }
  }

  async function handleLogout(): Promise<void> {
    await logout();
    currentActor = null;
    resetAuthenticatedState();
  }

  async function handleCreateUser(payload: CreateUserPayload): Promise<User> {
    const createdUser = await createUser(payload);
    await loadRoleData();
    return createdUser;
  }

  async function handleUpdateUserPassword(userId: number, password: string): Promise<void> {
    await updateUserPassword(userId, { password });
  }

  async function handleUpdateUserRole(userId: number, role: 'admin' | 'user'): Promise<User> {
    const updatedUser = await updateUserRole(userId, { role });
    if (currentActor?.id === userId) {
      currentActor = await getCurrentActor();
      await refreshAuthenticatedData(currentActor);
      return updatedUser;
    }
    await loadRoleData();
    return updatedUser;
  }

  async function handleStartQuiz(): Promise<void> {
    if (!currentActor) {
      quizError = 'Sign in before starting a quiz.';
      return;
    }
    quizError = '';
    try {
      session = await createQuizSession(selectedModuleId, quizQuestionCount);
    } catch (error) {
      quizError = error instanceof Error ? error.message : 'Unable to start a quiz.';
    }
  }

  async function handleSubmitAnswer(itemId: number, answers: string[]): Promise<void> {
    if (!session) {
      return;
    }
    quizBusyItemId = itemId;
    quizError = '';
    try {
      const result = await submitQuizAnswer(session.id, itemId, answers);
      session = applySubmitAnswerResult(session, itemId, result, new Date().toISOString());
    } catch (error) {
      quizError = error instanceof Error ? error.message : 'Unable to submit this answer.';
    } finally {
      quizBusyItemId = null;
    }
  }

  function handleToggleReviewOnly(value: boolean): void {
    reviewOnly = value;
  }

  function handleOpenCreate(): void {
    editorOrigin = 'default';
    editorMode = 'standard';
    editingRevisionProposal = null;
    editingQuestion = null;
    deletingQuestion = false;
    editorOpen = true;
  }

  function handleOpenEdit(question: QuestionRow): void {
    editorOrigin = 'default';
    editorMode = 'standard';
    editingRevisionProposal = null;
    deletingQuestion = false;
    editorOpen = true;
    editingQuestion = question;
  }

  async function handleOpenQuizEdit(questionId: number): Promise<void> {
    openingQuizEditorQuestionId = questionId;
    quizError = '';
    try {
      const question = await getQuestion(questionId);
      editorOrigin = 'quiz';
      editorMode = 'standard';
      editingRevisionProposal = null;
      deletingQuestion = false;
      editingQuestion = question;
      editorOpen = true;
    } catch (error) {
      quizError = error instanceof Error ? error.message : 'Unable to load this question for editing.';
    } finally {
      openingQuizEditorQuestionId = null;
    }
  }

  function handleOpenRevisionEditor(proposal: QuestionRevisionProposal): void {
    editorOrigin = 'default';
    editorMode = 'moderation';
    editingRevisionProposal = proposal;
    editingQuestion = buildModerationRevisionSeed(proposal, proposal.delete_requested ? 'current' : 'proposed');
    deletingQuestion = false;
    editorOpen = true;
  }

  function handleOpenUserRevisionEditor(proposal: QuestionRevisionProposal): void {
    editorOrigin = 'default';
    editorMode = 'standard';
    editingRevisionProposal = proposal;
    editingQuestion = buildModerationRevisionSeed(proposal, proposal.delete_requested ? 'current' : 'proposed');
    deletingQuestion = false;
    editorOpen = true;
  }

  function handleOpenImportForModule(moduleId: number): void {
    if (currentActor?.role !== 'admin') {
      return;
    }
    importState = openImportUiForModule(importState, moduleId);
  }

  async function handleExportContent(): Promise<void> {
    await exportContentArchive();
  }

  async function handleCreateModule(payload: CreateModulePayload): Promise<ModuleNode> {
    const created = await ensureModulePath({
      modules,
      parentId: payload.parent_id ?? null,
      titlePath: payload.title,
      instruction: payload.instruction,
      createModule,
      reloadModules: async () => {
        await refreshAuthenticatedData(currentActor);
        return modules;
      }
    });
    return created;
  }

  async function handleUpdateModule(moduleId: number, payload: UpdateModulePayload): Promise<ModuleNode> {
    const updated = await updateModule(moduleId, payload);
    await refreshAuthenticatedData(currentActor);
    return findModuleNodeInTree(modules, updated.id) ?? updated;
  }

  async function handleDeleteModule(moduleId: number): Promise<void> {
    await deleteModule(moduleId);
    await refreshAuthenticatedData(currentActor);
  }

  function closeEditor(): void {
    editorOpen = false;
    editorMode = 'standard';
    editorOrigin = 'default';
    editingQuestion = null;
    editingRevisionProposal = null;
    deletingQuestion = false;
  }

  async function reloadAfterQuestionMutation(): Promise<void> {
    session = null;
    await refreshAuthenticatedData();
    if (currentRoute !== 'stats') {
      await navigate('stats');
    }
  }

  async function reloadAfterModerationMutation(): Promise<void> {
    await refreshAuthenticatedData();
  }

  function markSessionQuestionInReview(questionId: number, proposalId: number): void {
    if (!session) {
      return;
    }
    session = {
      ...session,
      items: session.items.map((item) =>
        item.question_id === questionId
          ? { ...item, viewer_revision_proposal_id: proposalId }
          : item
      )
    };
  }

  async function handleSaveQuestion(payload: QuestionDraftPayload, resetStats: boolean): Promise<void> {
    savingQuestion = true;
    try {
      const origin = editorOrigin;
      const editedQuestionId = editingQuestion?.question_id ?? null;
      const savedMutation = await saveQuestionMutation({
        editorMode,
        editingQuestion,
        editingRevisionProposal,
        payload,
        resetStats,
        createQuestion,
        reviseQuestion,
        reviewQuestionRevision
      });
      if (origin === 'quiz' && editedQuestionId !== null && savedMutation.mutationResult?.proposal_id) {
        markSessionQuestionInReview(editedQuestionId, savedMutation.mutationResult.proposal_id);
      }
      closeEditor();
      if (savedMutation.reloadKind === 'moderation') {
        await reloadAfterModerationMutation();
      } else if (origin === 'quiz') {
        await refreshAuthenticatedData();
      } else {
        await reloadAfterQuestionMutation();
      }
    } finally {
      savingQuestion = false;
    }
  }

  async function handleDeleteQuestion(questionId: number): Promise<void> {
    deletingQuestion = true;
    try {
      const origin = editorOrigin;
      const mutationResult = await deleteQuestion(questionId);
      if (origin === 'quiz' && mutationResult.proposal_id) {
        markSessionQuestionInReview(questionId, mutationResult.proposal_id);
      }
      closeEditor();
      if (origin === 'quiz') {
        await refreshAuthenticatedData();
      } else {
        await reloadAfterQuestionMutation();
      }
    } finally {
      deletingQuestion = false;
    }
  }

  async function handleWithdrawRevision(questionId: number): Promise<void> {
    withdrawingRevisionQuestionId = questionId;
    try {
      await withdrawQuestionRevision(questionId);
      closeEditor();
      await refreshAuthenticatedData();
    } finally {
      withdrawingRevisionQuestionId = null;
    }
  }

  async function handleStartImport(qmlText: string): Promise<void> {
    importState = await startImportUiFlow({
      state: importState,
      actor: currentActor,
      moduleNode: importTargetModuleNode,
      qmlText,
      validateText: validateQuestionImportText,
      onStateChange: (nextState) => (importState = nextState),
      getState: () => importState
    });
  }

  async function handleCommitImport(rows: QuestionImportRowPayload[]): Promise<void> {
    const result = await commitImportUiFlow({
      state: importState,
      actor: currentActor,
      moduleNode: importTargetModuleNode,
      rows,
      validateRows: validateQuestionImportRows,
      commitRows: commitQuestionImport,
      chunkSize: IMPORT_COMMIT_CHUNK_SIZE,
      onStateChange: (nextState) => (importState = nextState),
      getState: () => importState
    });
    importState = result.state;
    if (result.committedAll) {
      await reloadAfterQuestionMutation();
    }
  }

  async function handleModerationAction(
    kind: ModerationKind,
    id: number,
    payload: ModerationRevisionActionPayload
  ): Promise<void> {
    if (kind === 'module') {
      await reviewModule(id, payload);
    } else if (kind === 'question') {
      await reviewQuestion(id, payload);
    } else {
      await reviewQuestionRevision(id, payload);
    }
    await reloadAfterModerationMutation();
  }

  async function handleDeleteRejectedModule(moduleId: number): Promise<void> {
    await deleteRejectedModule(moduleId);
    await reloadAfterModerationMutation();
  }

  async function handleBulkQuestionModeration(
    questionIds: number[],
    payload: ModerationActionPayload
  ): Promise<BulkModerationResult> {
    const result = await runBulkModeration({
      ids: questionIds,
      payload,
      handler: reviewQuestion
    });
    await reloadAfterModerationMutation();
    return result;
  }

  onMount(() => {
    currentRoute = routeFromPath(window.location.pathname);
    void resolveAuthSession();

    const handlePopstate = (): void => {
      currentRoute = routeFromPath(window.location.pathname);
      if (currentRoute === 'stats' && currentActor) {
        void loadStats();
      }
    };

    window.addEventListener('popstate', handlePopstate);
    return () => window.removeEventListener('popstate', handlePopstate);
  });

  $: selectedModuleLabel =
    selectedModuleId === null
      ? modules[0]?.title ?? 'Selected Module'
      : findModuleTitle(modules, selectedModuleId) ?? 'Selected Module';
  $: selectedModuleNode = selectedModuleId === null ? null : findModuleNodeInTree(modules, selectedModuleId);
  $: importTargetModuleNode =
    importState.targetModuleId === null ? null : findModuleNodeInTree(modules, importState.targetModuleId);
</script>

{#if authLoading}
  <section class="page">
    <div class="panel empty-state">
      <h3>Loading...</h3>
    </div>
  </section>
{:else if !currentActor}
  <AuthPage
    bootstrapRequired={health?.bootstrap_required ?? false}
    busy={authBusy}
    errorMessage={authError}
    onLogin={handleLogin}
    onBootstrapAdmin={handleBootstrapAdmin}
  />
{:else}
  <div class="app-shell">
    <div class="glow glow-one"></div>
    <div class="glow glow-two"></div>

    <Header
      currentRoute={currentRoute}
      currentActor={currentActor}
      onNavigate={navigate}
      onToggleMenu={() => (moduleMenuOpen = !moduleMenuOpen)}
      onLogout={handleLogout}
    />

    <ModuleMenu
      open={moduleMenuOpen}
      modules={modules}
      selectedModuleId={selectedModuleId}
      selectedModuleLabel={selectedModuleLabel}
      onClose={() => (moduleMenuOpen = false)}
      onSelect={handleSelectModule}
    />

    <main class="page-shell">
      {#if currentRoute === 'quiz'}
        <QuizPage
          session={session}
          moduleLabel={selectedModuleLabel}
          questionCount={quizQuestionCount}
          busyItemId={quizBusyItemId}
          openingEditorQuestionId={openingQuizEditorQuestionId}
          errorMessage={quizError}
          onChangeQuestionCount={(value) => (quizQuestionCount = value)}
          onStartQuiz={handleStartQuiz}
          onOpenEdit={handleOpenQuizEdit}
          onSubmit={handleSubmitAnswer}
        />
      {:else if currentRoute === 'stats'}
        <StatsPage
          moduleLabel={selectedModuleLabel}
          stats={stats}
          loading={statsLoading}
          reviewOnly={reviewOnly}
          errorMessage={statsError}
          currentActor={currentActor}
          onToggleReviewOnly={handleToggleReviewOnly}
          onOpenCreate={handleOpenCreate}
          onOpenEdit={handleOpenEdit}
          onOpenUserRevisionEditor={handleOpenUserRevisionEditor}
          onOpenAdminRevisionEditor={handleOpenRevisionEditor}
          onRevisionModeration={(id, payload) => handleModerationAction('revision', id, payload)}
          onWithdrawRevision={handleWithdrawRevision}
        />
      {:else}
        <AdminPage
          currentActor={currentActor}
          modules={modules}
          users={users}
          selectedModuleId={selectedModuleId}
          moderationQueue={moderationQueue}
          contributions={contributions}
          onCreateUser={handleCreateUser}
          onUpdateUserRole={handleUpdateUserRole}
          onUpdateUserPassword={handleUpdateUserPassword}
          onCreateModule={handleCreateModule}
          onUpdateModule={handleUpdateModule}
          onDeleteModule={handleDeleteModule}
          onOpenImport={handleOpenImportForModule}
          onExportContent={handleExportContent}
          onModerationAction={handleModerationAction}
          onDeleteRejectedModule={handleDeleteRejectedModule}
          onBulkQuestionModeration={handleBulkQuestionModeration}
        />
      {/if}
    </main>

    <EditorDrawer
      open={editorOpen}
      modules={modules}
      defaultModuleId={selectedModuleId}
      editingQuestion={editingQuestion}
      mode={editorMode}
      saving={savingQuestion}
      deleting={deletingQuestion}
      withdrawingRevision={withdrawingRevisionQuestionId === editingQuestion?.question_id}
      currentActor={currentActor}
      revisionProposal={editingRevisionProposal}
      onClose={closeEditor}
      onSave={handleSaveQuestion}
      onDelete={handleDeleteQuestion}
      onWithdrawRevision={handleWithdrawRevision}
    />

    <ImportDrawer
      open={currentActor?.role === 'admin' && importState.open}
      moduleNode={importTargetModuleNode}
      result={importState.result}
      busy={importState.busy}
      errorMessage={importState.error}
      draftText={importState.draftQmlText}
      draftRows={importState.draftRows}
      saveStatusMessageOverride={importState.saveStatusMessage}
      saveStatusToneOverride={importState.saveStatusTone}
      saveProgressTotal={importState.saveProgressTotal}
      saveProgressCompleted={importState.saveProgressCompleted}
      onClose={closeImportDrawer}
      onDraftChange={updateImportDraft}
      onStartImport={handleStartImport}
      onCommit={handleCommitImport}
    />
  </div>
{/if}
