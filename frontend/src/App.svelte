<script lang="ts">
  import { onMount } from 'svelte';
  import AdminPage from './components/AdminPage.svelte';
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
    findUser,
    moduleIdExists,
    persistActiveUser as persistActiveUserSelection,
    persistImportSession,
    persistSelectedModule as persistSelectedModuleSelection,
    restoreActiveUserId,
    restoreImportSession,
    restoreSelectedModuleId,
    routeFromPath
  } from './lib/app-state';
  import { IMPORT_COMMIT_CHUNK_SIZE, initialImportDraftRows } from './lib/import-session';
  import { cloneImportRows } from './lib/import-rows';
  import { commitImportInChunks, prepareImportSave, rebuildImportStateAfterPartialSave } from './lib/import-workflow';
  import {
    commitQuestionImport,
    createModule,
    createQuestion,
    createQuizSession,
    createUser,
    deleteQuestion,
    getHealth,
    getModulesTree,
    getStats,
    getUsers,
    reviseQuestion,
    setQuestionReviewFlag,
    submitQuizAnswer,
    updateModule,
    validateQuestionImportRows,
    validateQuestionImportText
  } from './lib/api';
  import { ensureModulePath, findModuleNode as findModuleNodeInTree } from './lib/module-paths';
  import { applyQuestionReviewFlag, applySubmitAnswerResult } from './lib/quiz-session';
  import type {
    CreateModulePayload,
    CreateUserPayload,
    HealthResponse,
    ModuleNode,
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

  let users: User[] = [];
  let activeUserId: number | null = null;

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

  function persistActiveUser(userId: number | null): void {
    persistActiveUserSelection(window.localStorage, {
      instanceKey,
      users,
      userId
    });
  }

  function persistSelectedModule(moduleId: number | null): void {
    persistSelectedModuleSelection(window.localStorage, {
      instanceKey,
      modules,
      moduleId
    });
  }

  function applyActiveUser(userId: number | null): void {
    activeUserId = userId;
    persistActiveUser(userId);
    session = null;
    quizError = '';
    stats = null;
    statsError = '';
  }

  function applySelectedModule(moduleId: number | null): void {
    selectedModuleId = moduleId;
    persistSelectedModule(moduleId);
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

  function hasSelectedModuleChanged(moduleId: number | null): boolean {
    return selectedModuleId !== moduleId;
  }

  async function handleSelectModule(moduleId: number | null, keepMenuOpen = false): Promise<void> {
    const moduleChanged = hasSelectedModuleChanged(moduleId);
    applySelectedModule(moduleId);
    moduleMenuOpen = keepMenuOpen;
    if (!moduleChanged) {
      return;
    }
    session = null;
    quizError = '';
    resetImportState(true);
    if (currentRoute === 'stats') {
      await loadStats();
    }
  }

  async function loadUsersAndRestoreSelection(): Promise<void> {
    const loadedUsers = await getUsers();
    users = loadedUsers;
    applyActiveUser(
      restoreActiveUserId(window.localStorage, {
        instanceKey,
        users: loadedUsers,
        activeUserId
      })
    );
  }

  async function loadStats(): Promise<void> {
    if (activeUserId === null) {
      stats = null;
      statsError = '';
      statsLoading = false;
      return;
    }

    statsLoading = true;
    statsError = '';
    try {
      stats = await getStats(activeUserId, selectedModuleId);
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
  }

  async function handleSelectUser(userId: number): Promise<void> {
    applyActiveUser(userId);
    if (currentRoute === 'stats') {
      await loadStats();
    }
  }

  async function handleCreateUser(payload: CreateUserPayload): Promise<User> {
    const createdUser = await createUser(payload);
    await loadUsersAndRestoreSelection();
    applyActiveUser(createdUser.id);
    if (currentRoute === 'stats') {
      await loadStats();
    }
    return createdUser;
  }

  async function handleStartQuiz(): Promise<void> {
    if (activeUserId === null) {
      quizError = 'Create a user in Admin or select one from the header before starting a quiz.';
      return;
    }
    quizError = '';
    try {
      session = await createQuizSession(activeUserId, selectedModuleId, quizQuestionCount);
    } catch (error) {
      quizError = error instanceof Error ? error.message : 'Unable to start a quiz.';
    }
  }

  async function handleSubmitAnswer(itemId: number, answers: string[]): Promise<void> {
    if (!session || activeUserId === null) {
      return;
    }
    quizBusyItemId = itemId;
    quizError = '';
    try {
      const result = await submitQuizAnswer(activeUserId, session.id, itemId, answers);
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
    if (!session || activeUserId === null) {
      return;
    }
    markingReviewQuestionId = questionId;
    quizError = '';
    try {
      await setQuestionReviewFlag(activeUserId, questionId, true);
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
    resetImportState();
    importTargetModuleId = moduleId;
    importDrawerOpen = true;
  }

  async function handleCreateModule(payload: CreateModulePayload): Promise<ModuleNode> {
    return ensureModulePath({
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
  }

  async function handleUpdateModule(moduleId: number, payload: UpdateModulePayload): Promise<ModuleNode> {
    const updated = await updateModule(moduleId, payload);
    await loadModules();
    return findModuleNode(modules, updated.id) ?? updated;
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
        await createQuestion(activeUserId, payload);
      }
      editorOpen = false;
      editingQuestion = null;
      session = null;
      if (currentRoute !== 'stats') {
        await navigate('stats');
      } else {
        await loadStats();
      }
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
      session = null;
      if (currentRoute !== 'stats') {
        await navigate('stats');
      } else {
        await loadStats();
      }
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

      const validationStatus = saveStatus ?? (queue.length === 0 ? { message: 'Nothing new to save.', tone: 'info' as const } : null);
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
      session = null;
      if (currentRoute === 'stats') {
        await loadStats();
      }
    } catch (error) {
      if (importSaveProgressCompleted > 0) {
        try {
          const rebuiltState = await rebuildImportStateAfterPartialSave({
            moduleId: importTargetModuleNode.id,
            rows: importDraftRows,
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

  onMount(() => {
    currentRoute = routeFromPath(window.location.pathname);
    void (async () => {
      let health: HealthResponse | null = null;
      try {
        health = await getHealth();
      } catch (error) {
        console.error(error);
      }
      instanceKey = health?.instance_key?.trim() || 'default';
      clearLegacySelectionStorage(window.localStorage);
      await loadModules();
      restoreImportStateFromSession();
      importSessionReady = true;
      await loadUsersAndRestoreSelection();
      if (currentRoute === 'stats') {
        await loadStats();
      }
    })();

    const handlePopstate = (): void => {
      currentRoute = routeFromPath(window.location.pathname);
      if (currentRoute === 'stats') {
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
  $: activeUser = findUser(users, activeUserId);
  $: activeUserLabel = activeUser?.display_name ?? 'No user selected';
  $: showUserGate = currentRoute !== 'admin' && activeUserId === null;
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

<div class="app-shell">
  <div class="glow glow-one"></div>
  <div class="glow glow-two"></div>

  <Header
    currentRoute={currentRoute}
    users={users}
    activeUserId={activeUserId}
    onNavigate={navigate}
    onToggleMenu={() => (moduleMenuOpen = !moduleMenuOpen)}
    onSelectUser={handleSelectUser}
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
    {#if showUserGate}
      <section class="page">
        <div class="panel empty-state user-gate-panel">
          <p class="eyebrow">Active user required</p>
          <h2>Create a user in Admin</h2>
          <p class="muted-copy">Quiz progress, review flags, and stats belong to a specific user.</p>
          <button class="primary-button" type="button" on:click={() => void navigate('admin')}>
            Open Admin
          </button>
        </div>
      </section>
    {:else if currentRoute === 'quiz'}
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
        activeUserLabel={activeUserLabel}
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
        modules={modules}
        users={users}
        activeUser={activeUser}
        selectedModuleId={selectedModuleId}
        onCreateUser={handleCreateUser}
        onCreateModule={handleCreateModule}
        onUpdateModule={handleUpdateModule}
        onOpenImport={handleOpenImportForModule}
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
    onClose={() => resetImportState(true)}
    onDraftChange={updateImportDraft}
    onStartImport={handleStartImport}
    onCommit={handleCommitImport}
  />
</div>
