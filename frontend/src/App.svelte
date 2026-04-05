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
    commitQuestionImportSession,
    createModule,
    createQuestion,
    createQuestionImportSession,
    createQuizSession,
    createUser,
    discardQuestionImportSessionRow,
    getModulesTree,
    getStats,
    getUsers,
    revalidateQuestionImportSession,
    reviseQuestion,
    setQuestionReviewFlag,
    submitQuizAnswer
  } from './lib/api';
  import { ensureModulePath, findModuleNode as findModuleNodeInTree } from './lib/module-paths';
  import type {
    CreateModulePayload,
    ModuleNode,
    QuestionDraftPayload,
    QuestionImportRowPayload,
    QuestionImportSession,
    QuestionRow,
    QuizSession,
    RouteName,
    StatsResponse,
    User
  } from './lib/types';

  const ACTIVE_USER_STORAGE_KEY = 'learning.active-user-id';

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

  let stats: StatsResponse | null = null;
  let statsLoading = false;
  let statsError = '';
  let reviewOnly = false;

  let editorOpen = false;
  let editingQuestion: QuestionRow | null = null;
  let savingQuestion = false;

  let importDrawerOpen = false;
  let importTargetModuleId: number | null = null;
  let importSession: QuestionImportSession | null = null;
  let importBusy = false;
  let importError = '';

  function routeFromPath(pathname: string): RouteName {
    if (pathname.startsWith('/stats')) {
      return 'stats';
    }
    if (pathname.startsWith('/admin')) {
      return 'admin';
    }
    return 'quiz';
  }

  function findModuleNode(nodes: ModuleNode[], moduleId: number): ModuleNode | null {
    return findModuleNodeInTree(nodes, moduleId);
  }

  function findModuleTitle(nodes: ModuleNode[], moduleId: number): string | null {
    return findModuleNode(nodes, moduleId)?.title ?? null;
  }

  function moduleIdExists(nodes: ModuleNode[], moduleId: number): boolean {
    return findModuleNode(nodes, moduleId) !== null;
  }

  function findUser(usersList: User[], userId: number | null): User | null {
    if (userId === null) {
      return null;
    }
    return usersList.find((user) => user.id === userId) ?? null;
  }

  function persistActiveUser(userId: number | null): void {
    if (userId === null) {
      window.localStorage.removeItem(ACTIVE_USER_STORAGE_KEY);
      return;
    }
    window.localStorage.setItem(ACTIVE_USER_STORAGE_KEY, String(userId));
  }

  function applyActiveUser(userId: number | null): void {
    activeUserId = userId;
    persistActiveUser(userId);
    session = null;
    quizError = '';
    stats = null;
    statsError = '';
  }

  function resetImportState(closeDrawer = false): void {
    importSession = null;
    importError = '';
    importBusy = false;
    if (closeDrawer) {
      importDrawerOpen = false;
      importTargetModuleId = null;
    }
  }

  async function loadModules(): Promise<void> {
    const loadedModules = await getModulesTree();
    modules = loadedModules;
    if (importTargetModuleId !== null && !moduleIdExists(loadedModules, importTargetModuleId)) {
      importTargetModuleId = null;
    }
    if (loadedModules.length === 0) {
      selectedModuleId = null;
      return;
    }
    if (selectedModuleId === null || !moduleIdExists(loadedModules, selectedModuleId)) {
      selectedModuleId = loadedModules[0].id;
    }
  }

  async function loadUsersAndRestoreSelection(): Promise<void> {
    const loadedUsers = await getUsers();
    users = loadedUsers;

    const currentUser = findUser(loadedUsers, activeUserId);
    if (currentUser) {
      return;
    }

    const savedUserId = Number(window.localStorage.getItem(ACTIVE_USER_STORAGE_KEY));
    if (Number.isFinite(savedUserId) && findUser(loadedUsers, savedUserId)) {
      applyActiveUser(savedUserId);
      return;
    }

    if (loadedUsers.length > 0) {
      applyActiveUser(loadedUsers[0].id);
      return;
    }

    applyActiveUser(null);
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
      stats = await getStats(activeUserId, selectedModuleId, reviewOnly);
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

  async function handleSelectModule(moduleId: number | null, keepMenuOpen = false): Promise<void> {
    selectedModuleId = moduleId;
    moduleMenuOpen = keepMenuOpen;
    session = null;
    quizError = '';
    resetImportState(true);
    if (currentRoute === 'stats') {
      await loadStats();
    }
  }

  async function handleSelectUser(userId: number): Promise<void> {
    applyActiveUser(userId);
    if (currentRoute === 'stats') {
      await loadStats();
    }
  }

  async function handleCreateUser(payload: { handle: string; display_name: string }): Promise<User> {
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
      session = await createQuizSession(activeUserId, selectedModuleId, 10);
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
      session = {
        ...session,
        completed_at: result.session_completed ? new Date().toISOString() : session.completed_at,
        items: session.items.map((item) =>
          item.id === itemId
            ? {
                ...item,
                submitted_answer: result.submitted_answer,
                is_correct: result.is_correct,
                score_earned: result.score_earned,
                score_possible: result.score_possible,
                slot_results: result.slot_results,
                canonical_answers: result.canonical_answers
              }
            : item
        )
      };
    } catch (error) {
      quizError = error instanceof Error ? error.message : 'Unable to submit this answer.';
    } finally {
      quizBusyItemId = null;
    }
  }

  async function handleToggleReviewOnly(value: boolean): Promise<void> {
    reviewOnly = value;
    await loadStats();
  }

  async function handleMarkForRevision(questionId: number): Promise<void> {
    if (!session || activeUserId === null) {
      return;
    }
    markingReviewQuestionId = questionId;
    quizError = '';
    try {
      await setQuestionReviewFlag(activeUserId, questionId, true);
      session = {
        ...session,
        items: session.items.map((item) =>
          item.question_id === questionId
            ? {
                ...item,
                review_flag: true
              }
            : item
        )
      };
    } catch (error) {
      quizError = error instanceof Error ? error.message : 'Unable to mark this question for revision.';
    } finally {
      markingReviewQuestionId = null;
    }
  }

  function handleOpenCreate(): void {
    editingQuestion = null;
    editorOpen = true;
  }

  function handleOpenEdit(question: QuestionRow): void {
    editorOpen = true;
    editingQuestion = question;
  }

  function handleOpenImportForModule(moduleId: number): void {
    importError = '';
    importSession = null;
    importTargetModuleId = moduleId;
    importDrawerOpen = true;
  }

  async function handleCreateModule(payload: CreateModulePayload): Promise<ModuleNode> {
    return ensureModulePath({
      modules,
      parentId: payload.parent_id ?? null,
      titlePath: payload.title,
      instruction: payload.instruction,
      uiCopy: payload.ui_copy,
      createModule,
      reloadModules: async () => {
        await loadModules();
        return modules;
      }
    });
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

  async function handleStartImport(csvText: string): Promise<void> {
    if (!importTargetModuleNode) {
      return;
    }
    importBusy = true;
    importError = '';
    try {
      importSession = await createQuestionImportSession(importTargetModuleNode.id, csvText);
    } catch (error) {
      importError = error instanceof Error ? error.message : 'Unable to start this upload.';
    } finally {
      importBusy = false;
    }
  }

  async function handleRevalidateImport(rows: QuestionImportRowPayload[]): Promise<void> {
    if (!importSession) {
      return;
    }
    importBusy = true;
    importError = '';
    try {
      importSession = await revalidateQuestionImportSession(importSession.session_id, rows);
    } catch (error) {
      importError = error instanceof Error ? error.message : 'Unable to revalidate this upload.';
    } finally {
      importBusy = false;
    }
  }

  async function handleDiscardImportRow(rowNumber: number): Promise<void> {
    if (!importSession) {
      return;
    }
    importBusy = true;
    importError = '';
    try {
      importSession = await discardQuestionImportSessionRow(importSession.session_id, rowNumber);
    } catch (error) {
      importError = error instanceof Error ? error.message : 'Unable to discard this row.';
    } finally {
      importBusy = false;
    }
  }

  async function handleCommitImport(): Promise<void> {
    if (!importSession) {
      return;
    }
    importBusy = true;
    importError = '';
    try {
      const nextState = await commitQuestionImportSession(importSession.session_id);
      if (nextState.committed) {
        resetImportState(true);
        session = null;
        if (currentRoute === 'stats') {
          await loadStats();
        }
        return;
      }
      importSession = nextState;
    } catch (error) {
      importError = error instanceof Error ? error.message : 'Unable to commit this upload.';
    } finally {
      importBusy = false;
    }
  }

  onMount(() => {
    currentRoute = routeFromPath(window.location.pathname);
    void (async () => {
      await loadModules();
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
        busyItemId={quizBusyItemId}
        markingReviewQuestionId={markingReviewQuestionId}
        errorMessage={quizError}
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
        onCreateUser={handleCreateUser}
        onCreateModule={handleCreateModule}
        onOpenImport={handleOpenImportForModule}
      />
    {/if}
  </main>

  <EditorDrawer
    open={editorOpen}
    modules={modules}
    editingQuestion={editingQuestion}
    saving={savingQuestion}
    onClose={() => (editorOpen = false)}
    onSave={handleSaveQuestion}
  />

  <ImportDrawer
    open={importDrawerOpen}
    moduleNode={importTargetModuleNode}
    session={importSession}
    busy={importBusy}
    errorMessage={importError}
    onClose={() => resetImportState(true)}
    onStartImport={handleStartImport}
    onRevalidate={handleRevalidateImport}
    onDiscardRow={handleDiscardImportRow}
    onCommit={handleCommitImport}
  />
</div>
