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
  import {
    clearImportSessionStorage,
    clearLegacySelectionStorage,
    findModuleTitle,
    moduleIdExists,
    persistImportSession,
    persistSelectedModule as persistSelectedModuleSelection,
    restoreImportSession,
    restoreSelectedModuleId,
    routeFromPath
  } from './lib/app-state';
  import { IMPORT_COMMIT_CHUNK_SIZE, initialImportDraftRows } from './lib/import-session';
  import { cloneImportRows } from './lib/import-rows';
  import { commitImportInChunks, prepareImportSave, rebuildImportStateAfterPartialSave } from './lib/import-workflow';
  import {
    bootstrapAdmin,
    commitQuestionImport,
    createDemoSession,
    createModule,
    createQuestion,
    createQuizSession,
    createUser,
    deleteQuestion,
    getCurrentActor,
    getHealth,
    getModerationQueue,
    getModulesTree,
    getMyContributions,
    getStats,
    getUsers,
    login,
    logout,
    reviewModule,
    reviewQuestion,
    reviewQuestionRevision,
    reviseQuestion,
    setQuestionReviewFlag,
    submitQuizAnswer,
    updateModule,
    updateUserPassword,
    updateUserRole,
    validateQuestionImportRows,
    validateQuestionImportText
  } from './lib/api';
  import { ensureModulePath, findModuleNode as findModuleNodeInTree } from './lib/module-paths';
  import { applyQuestionReviewFlag, applySubmitAnswerResult } from './lib/quiz-session';
  import type {
    AuthActor,
    CreateModulePayload,
    CreateUserPayload,
    HealthResponse,
    ModerationActionPayload,
    ModerationQueue,
    ModuleNode,
    MyContributions,
    QuestionDraftPayload,
    QuestionImportResult,
    QuestionImportRowPayload,
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
  let markingReviewQuestionId: number | null = null;
  let quizError = '';
  let quizQuestionCount = 10;

  let stats: StatsResponse | null = null;
  let statsLoading = false;
  let statsError = '';
  let reviewOnly = false;

  let editorOpen = false;
  let editingQuestion: QuestionRow | null = null;
  let savingQuestion = false;
  let deletingQuestion = false;

  let importDrawerOpen = false;
  let importTargetModuleId: number | null = null;
  let importResult: QuestionImportResult | null = null;
  let importBusy = false;
  let importError = '';
  let importDraftQmlText = '';
  let importDraftRows: QuestionImportRowPayload[] = [];
  let importSaveStatusMessage = '';
  let importSaveStatusTone: 'error' | 'info' | '' = '';
  let importSaveProgressTotal = 0;
  let importSaveProgressCompleted = 0;
  let importSessionReady = false;
  let instanceKey = 'default';

  function findModuleNode(nodes: ModuleNode[], moduleId: number): ModuleNode | null {
    return findModuleNodeInTree(nodes, moduleId);
  }

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
    users = [];
    moderationQueue = null;
    contributions = null;
    reviewOnly = false;
    moduleMenuOpen = false;
    resetImportState(true);
  }

  function resetImportState(closeDrawer = false): void {
    importResult = null;
    importError = '';
    importBusy = false;
    importDraftQmlText = '';
    importDraftRows = [];
    importSaveStatusMessage = '';
    importSaveStatusTone = '';
    importSaveProgressTotal = 0;
    importSaveProgressCompleted = 0;
    if (closeDrawer) {
      importDrawerOpen = false;
      importTargetModuleId = null;
    }
  }

  function closeImportDrawer(): void {
    if (importBusy) {
      importDrawerOpen = false;
      return;
    }
    resetImportState(true);
  }

  function reopenImportDrawer(): void {
    if (importTargetModuleId === null) {
      return;
    }
    importDrawerOpen = true;
  }

  function updateImportDraft(qmlText: string, rows: QuestionImportRowPayload[]): void {
    importDraftQmlText = qmlText;
    importDraftRows = rows.map((row) => ({
      row_number: row.row_number,
      qml_line: row.qml_line
    }));
  }

  function setImportSaveStatus(message = '', tone: 'error' | 'info' | '' = ''): void {
    importSaveStatusMessage = message;
    importSaveStatusTone = tone;
  }

  function restoreImportStateFromSession(): void {
    const restored = restoreImportSession(window.sessionStorage, {
      instanceKey,
      modules
    });

    resetImportState(true);
    if (!restored) {
      clearImportSessionStorage(window.sessionStorage, instanceKey);
      return;
    }

    importDrawerOpen = true;
    importTargetModuleId = restored.targetModuleId;
    importDraftQmlText = restored.qmlText;
    importDraftRows = restored.rows;
    importResult = restored.result;
  }

  async function loadModules(): Promise<void> {
    if (!currentActor) {
      modules = [];
      applySelectedModule(null);
      return;
    }

    const loadedModules = await getModulesTree();
    modules = loadedModules;
    if (importTargetModuleId !== null && !moduleIdExists(loadedModules, importTargetModuleId)) {
      importTargetModuleId = null;
    }
    if (loadedModules.length === 0) {
      applySelectedModule(null);
      return;
    }
    applySelectedModule(
      restoreSelectedModuleId(window.localStorage, {
        instanceKey,
        modules: loadedModules,
        selectedModuleId
      })
    );
  }

  async function loadRoleData(): Promise<void> {
    if (!currentActor || currentActor.is_demo) {
      users = [];
      moderationQueue = null;
      contributions = null;
      return;
    }
    if (currentActor.role === 'admin') {
      users = await getUsers();
      moderationQueue = await getModerationQueue();
      contributions = null;
      return;
    }
    users = [];
    moderationQueue = null;
    contributions = await getMyContributions();
  }

  async function refreshAuthenticatedData(): Promise<void> {
    await loadModules();
    restoreImportStateFromSession();
    importSessionReady = true;
    await loadRoleData();
    if (currentRoute === 'stats') {
      await loadStats();
    }
  }

  async function resolveAuthSession(): Promise<void> {
    authLoading = true;
    authError = '';
    try {
      health = await getHealth();
      instanceKey = health?.instance_key?.trim() || 'default';
    } catch (error) {
      console.error(error);
      health = { status: 'ok', instance_key: 'default', bootstrap_required: false };
    }

    clearLegacySelectionStorage(window.localStorage);

    try {
      currentActor = await getCurrentActor();
      await refreshAuthenticatedData();
    } catch (error) {
      currentActor = null;
      resetAuthenticatedState();
      importSessionReady = true;
    } finally {
      authLoading = false;
    }
  }

  async function loadStats(): Promise<void> {
    if (!currentActor) {
      stats = null;
      statsError = '';
      statsLoading = false;
      return;
    }

    statsLoading = true;
    statsError = '';
    try {
      stats = await getStats(selectedModuleId);
    } catch (error) {
      statsError = error instanceof Error ? error.message : 'Unable to load stats.';
    } finally {
      statsLoading = false;
    }
  }

  async function navigate(route: RouteName): Promise<void> {
    currentRoute = route;
    window.history.pushState({}, '', route === 'quiz' ? '/quiz' : route === 'stats' ? '/stats' : '/admin');
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
      await refreshAuthenticatedData();
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
      await refreshAuthenticatedData();
    } catch (error) {
      authError = error instanceof Error ? error.message : 'Unable to create the first admin.';
    } finally {
      authBusy = false;
    }
  }

  async function handleDemoSession(): Promise<void> {
    authBusy = true;
    authError = '';
    try {
      currentActor = await createDemoSession();
      await refreshAuthenticatedData();
    } catch (error) {
      authError = error instanceof Error ? error.message : 'Unable to start demo mode.';
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
      await refreshAuthenticatedData();
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

  async function handleMarkForRevision(questionId: number): Promise<void> {
    if (!session) {
      return;
    }
    markingReviewQuestionId = questionId;
    quizError = '';
    try {
      await setQuestionReviewFlag(questionId, true);
      session = applyQuestionReviewFlag(session, questionId, true);
    } catch (error) {
      quizError = error instanceof Error ? error.message : 'Unable to mark this question for revision.';
    } finally {
      markingReviewQuestionId = null;
    }
  }

  function handleOpenCreate(): void {
    editingQuestion = null;
    deletingQuestion = false;
    editorOpen = true;
  }

  function handleOpenEdit(question: QuestionRow): void {
    deletingQuestion = false;
    editorOpen = true;
    editingQuestion = question;
  }

  function handleOpenImportForModule(moduleId: number): void {
    if (importBusy && importTargetModuleId !== null) {
      importDrawerOpen = true;
      return;
    }
    resetImportState();
    importTargetModuleId = moduleId;
    importDrawerOpen = true;
  }

  async function handleCreateModule(payload: CreateModulePayload): Promise<ModuleNode> {
    const created = await ensureModulePath({
      modules,
      parentId: payload.parent_id ?? null,
      titlePath: payload.title,
      instruction: payload.instruction,
      createModule,
      reloadModules: async () => {
        await loadModules();
        return modules;
      }
    });
    await loadRoleData();
    return created;
  }

  async function handleUpdateModule(moduleId: number, payload: UpdateModulePayload): Promise<ModuleNode> {
    const updated = await updateModule(moduleId, payload);
    await loadModules();
    await loadRoleData();
    return findModuleNode(modules, updated.id) ?? updated;
  }

  async function reloadAfterQuestionMutation(): Promise<void> {
    session = null;
    await loadModules();
    await loadRoleData();
    if (currentRoute !== 'stats') {
      await navigate('stats');
    } else {
      await loadStats();
    }
  }

  async function handleSaveQuestion(payload: QuestionDraftPayload, resetStats: boolean): Promise<void> {
    savingQuestion = true;
    try {
      if (editingQuestion) {
        await reviseQuestion(editingQuestion.question_id, {
          ...payload,
          reset_stats: resetStats
        });
      } else {
        await createQuestion(payload);
      }
      editorOpen = false;
      editingQuestion = null;
      await reloadAfterQuestionMutation();
    } finally {
      savingQuestion = false;
    }
  }

  async function handleDeleteQuestion(questionId: number): Promise<void> {
    deletingQuestion = true;
    try {
      await deleteQuestion(questionId);
      editorOpen = false;
      editingQuestion = null;
      await reloadAfterQuestionMutation();
    } finally {
      deletingQuestion = false;
    }
  }

  async function handleStartImport(qmlText: string): Promise<void> {
    if (!importTargetModuleNode) {
      return;
    }
    importBusy = true;
    importError = '';
    setImportSaveStatus();
    importSaveProgressTotal = 0;
    importSaveProgressCompleted = 0;
    importDraftQmlText = qmlText;
    try {
      const nextResult = await validateQuestionImportText(importTargetModuleNode.id, qmlText);
      importDraftRows = initialImportDraftRows(nextResult);
      importResult = nextResult;
    } catch (error) {
      importError = error instanceof Error ? error.message : 'Unable to start this import.';
    } finally {
      importBusy = false;
    }
  }

  async function handleCommitImport(rows: QuestionImportRowPayload[]): Promise<void> {
    if (!importTargetModuleNode) {
      return;
    }
    let queuedRows: QuestionImportRowPayload[] = [];
    importBusy = true;
    importError = '';
    setImportSaveStatus();
    importDraftRows = cloneImportRows(rows);
    try {
      const { validatedState, draftRows, queue, saveStatus } = await prepareImportSave({
        moduleId: importTargetModuleNode.id,
        rows,
        validateRows: validateQuestionImportRows
      });
      importResult = validatedState;
      importDraftRows = draftRows;
      queuedRows = queue;

      const validationStatus =
        saveStatus ?? (queue.length === 0 ? { message: 'Nothing new to save.', tone: 'info' as const } : null);
      if (validationStatus) {
        setImportSaveStatus(validationStatus.message, validationStatus.tone);
        importSaveProgressTotal = 0;
        importSaveProgressCompleted = 0;
        return;
      }

      const commitResult = await commitImportInChunks({
        moduleId: importTargetModuleNode.id,
        rows: queue,
        commitRows: commitQuestionImport,
        chunkSize: IMPORT_COMMIT_CHUNK_SIZE,
        onProgress: ({ completed, total }) => {
          importSaveProgressCompleted = completed;
          importSaveProgressTotal = total;
        }
      });
      if (!commitResult.completed) {
        const rebuiltState = await rebuildImportStateAfterPartialSave({
          moduleId: importTargetModuleNode.id,
          rows: commitResult.remainingRows,
          committedRows: commitResult.committedRows,
          validateRows: validateQuestionImportRows
        });
        importDraftRows = rebuiltState.draftRows;
        importResult = rebuiltState.validatedState;
        setImportSaveStatus(rebuiltState.saveStatus.message, rebuiltState.saveStatus.tone);
        return;
      }

      resetImportState(true);
      await reloadAfterQuestionMutation();
    } catch (error) {
      if (importSaveProgressCompleted > 0 && queuedRows.length > 0) {
        try {
          const remainingRows = queuedRows.slice(importSaveProgressCompleted);
          const rebuiltState = await rebuildImportStateAfterPartialSave({
            moduleId: importTargetModuleNode.id,
            rows: remainingRows,
            committedRows: importSaveProgressCompleted,
            validateRows: validateQuestionImportRows
          });
          importDraftRows = rebuiltState.draftRows;
          importResult = rebuiltState.validatedState;
          setImportSaveStatus(rebuiltState.saveStatus.message, rebuiltState.saveStatus.tone);
        } catch (rebuildError) {
          console.error(rebuildError);
          importError = error instanceof Error ? error.message : 'Unable to commit this upload.';
        }
      } else {
        importError = error instanceof Error ? error.message : 'Unable to commit this upload.';
      }
    } finally {
      importBusy = false;
      importSaveProgressTotal = 0;
      importSaveProgressCompleted = 0;
    }
  }

  async function handleModerationAction(
    kind: 'module' | 'question' | 'revision',
    id: number,
    payload: ModerationActionPayload
  ): Promise<void> {
    if (kind === 'module') {
      await reviewModule(id, payload);
    } else if (kind === 'question') {
      await reviewQuestion(id, payload);
    } else {
      await reviewQuestionRevision(id, payload);
    }
    await loadRoleData();
    await loadModules();
    if (currentRoute === 'stats') {
      await loadStats();
    }
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
  $: selectedModuleNode = selectedModuleId === null ? null : findModuleNode(modules, selectedModuleId);
  $: selectedModuleIsLeaf = Boolean(selectedModuleNode && selectedModuleNode.children.length === 0);
  $: selectedModuleInstruction = selectedModuleNode?.instruction ?? '';
  $: importTargetModuleNode = importTargetModuleId === null ? null : findModuleNode(modules, importTargetModuleId);
  $: activeActorLabel = currentActor?.display_name ?? 'Current account';
  $: importStatusVisible =
    importTargetModuleId !== null &&
    !importDrawerOpen &&
    (importBusy || Boolean(importError) || Boolean(importSaveStatusMessage));
  $: importStatusTone = importBusy ? 'progress' : importError || importSaveStatusTone === 'error' ? 'error' : 'info';
  $: importStatusLabel = (() => {
    if (importBusy && importSaveProgressTotal > 0) {
      return `Uploading ${importSaveProgressCompleted}/${importSaveProgressTotal}`;
    }
    if (importBusy) {
      return importResult ? 'Saving import...' : 'Preparing import...';
    }
    if (importError) {
      return 'Import failed';
    }
    return importSaveStatusTone === 'error' ? 'Import needs attention' : 'Import updated';
  })();
  $: importStatusDetail = importError || importSaveStatusMessage || importStatusLabel;
  $: if (importSessionReady) {
    persistImportSession(window.sessionStorage, {
      instanceKey,
      modules,
      open: importDrawerOpen,
      targetModuleId: importTargetModuleId,
      qmlText: importDraftQmlText,
      rows: importDraftRows,
      result: importResult
    });
  }
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
    onDemo={handleDemoSession}
  />
{:else}
  <div class="app-shell">
    <div class="glow glow-one"></div>
    <div class="glow glow-two"></div>

    <Header
      currentRoute={currentRoute}
      currentActor={currentActor}
      importStatusVisible={importStatusVisible}
      importStatusLabel={importStatusLabel}
      importStatusDetail={importStatusDetail}
      importStatusTone={importStatusTone}
      onNavigate={navigate}
      onToggleMenu={() => (moduleMenuOpen = !moduleMenuOpen)}
      onOpenImportStatus={reopenImportDrawer}
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
          moduleInstruction={selectedModuleInstruction}
          selectedModuleIsLeaf={selectedModuleIsLeaf}
          questionCount={quizQuestionCount}
          busyItemId={quizBusyItemId}
          markingReviewQuestionId={markingReviewQuestionId}
          errorMessage={quizError}
          onChangeQuestionCount={(value) => (quizQuestionCount = value)}
          onStartQuiz={handleStartQuiz}
          onMarkForRevision={handleMarkForRevision}
          onSubmit={handleSubmitAnswer}
        />
      {:else if currentRoute === 'stats'}
        <StatsPage
          moduleLabel={selectedModuleLabel}
          activeUserLabel={activeActorLabel}
          stats={stats}
          loading={statsLoading}
          reviewOnly={reviewOnly}
          errorMessage={statsError}
          onToggleReviewOnly={handleToggleReviewOnly}
          onOpenCreate={handleOpenCreate}
          onOpenEdit={handleOpenEdit}
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
          onOpenImport={handleOpenImportForModule}
          onModerationAction={handleModerationAction}
        />
      {/if}
    </main>

    <EditorDrawer
      open={editorOpen}
      modules={modules}
      defaultModuleId={selectedModuleId}
      editingQuestion={editingQuestion}
      saving={savingQuestion}
      deleting={deletingQuestion}
      currentActor={currentActor}
      onClose={() => (editorOpen = false)}
      onSave={handleSaveQuestion}
      onDelete={handleDeleteQuestion}
    />

    <ImportDrawer
      open={importDrawerOpen}
      moduleNode={importTargetModuleNode}
      result={importResult}
      busy={importBusy}
      errorMessage={importError}
      draftText={importDraftQmlText}
      draftRows={importDraftRows}
      saveStatusMessageOverride={importSaveStatusMessage}
      saveStatusToneOverride={importSaveStatusTone}
      saveProgressTotal={importSaveProgressTotal}
      saveProgressCompleted={importSaveProgressCompleted}
      onClose={closeImportDrawer}
      onDraftChange={updateImportDraft}
      onStartImport={handleStartImport}
      onCommit={handleCommitImport}
    />
  </div>
{/if}
