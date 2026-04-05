<script lang="ts">
  import { onMount } from 'svelte';
  import EditorDrawer from './components/EditorDrawer.svelte';
  import Header from './components/Header.svelte';
  import ModuleMenu from './components/ModuleMenu.svelte';
  import QuizPage from './components/QuizPage.svelte';
  import StatsPage from './components/StatsPage.svelte';
  import {
    createModule,
    createQuestion,
    createQuizSession,
    getModulesTree,
    getStats,
    reviseQuestion,
    setQuestionReviewFlag,
    submitQuizAnswer
  } from './lib/api';
  import type {
    CreateModulePayload,
    ModuleNode,
    QuestionDraftPayload,
    QuestionRow,
    QuizSession,
    RouteName,
    StatsResponse
  } from './lib/types';

  let currentRoute: RouteName = 'quiz';
  let modules: ModuleNode[] = [];
  let selectedModuleId: number | null = null;
  let moduleMenuOpen = false;

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

  function routeFromPath(pathname: string): RouteName {
    return pathname.startsWith('/stats') ? 'stats' : 'quiz';
  }

  function findModuleTitle(nodes: ModuleNode[], moduleId: number): string | null {
    for (const node of nodes) {
      if (node.id === moduleId) {
        return node.title;
      }
      const child = findModuleTitle(node.children, moduleId);
      if (child) {
        return child;
      }
    }
    return null;
  }

  function moduleIdExists(nodes: ModuleNode[], moduleId: number): boolean {
    for (const node of nodes) {
      if (node.id === moduleId) {
        return true;
      }
      if (moduleIdExists(node.children, moduleId)) {
        return true;
      }
    }
    return false;
  }

  async function loadModules(): Promise<void> {
    const loadedModules = await getModulesTree();
    modules = loadedModules;
    if (loadedModules.length === 0) {
      selectedModuleId = null;
      return;
    }
    if (selectedModuleId === null || !moduleIdExists(loadedModules, selectedModuleId)) {
      selectedModuleId = loadedModules[0].id;
    }
  }

  async function loadStats(): Promise<void> {
    statsLoading = true;
    statsError = '';
    try {
      stats = await getStats(selectedModuleId, reviewOnly);
    } catch (error) {
      statsError = error instanceof Error ? error.message : 'Unable to load stats.';
    } finally {
      statsLoading = false;
    }
  }

  async function navigate(route: RouteName): Promise<void> {
    currentRoute = route;
    window.history.pushState({}, '', route === 'quiz' ? '/quiz' : '/stats');
    if (route === 'stats') {
      await loadStats();
    }
  }

  async function handleSelectModule(moduleId: number | null, keepMenuOpen = false): Promise<void> {
    selectedModuleId = moduleId;
    moduleMenuOpen = keepMenuOpen;
    session = null;
    quizError = '';
    if (currentRoute === 'stats') {
      await loadStats();
    }
  }

  async function handleStartQuiz(): Promise<void> {
    quizError = '';
    try {
      session = await createQuizSession(selectedModuleId, 10);
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
    if (!session) {
      return;
    }
    markingReviewQuestionId = questionId;
    quizError = '';
    try {
      await setQuestionReviewFlag(questionId, true);
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

  async function handleCreateModule(payload: CreateModulePayload): Promise<ModuleNode> {
    const created = await createModule(payload);
    await loadModules();
    return created;
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

  onMount(() => {
    currentRoute = routeFromPath(window.location.pathname);
    void (async () => {
      await loadModules();
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
</script>

<div class="app-shell">
  <div class="glow glow-one"></div>
  <div class="glow glow-two"></div>

  <Header
    currentRoute={currentRoute}
    onNavigate={navigate}
    onToggleMenu={() => (moduleMenuOpen = !moduleMenuOpen)}
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
        busyItemId={quizBusyItemId}
        markingReviewQuestionId={markingReviewQuestionId}
        errorMessage={quizError}
        onStartQuiz={handleStartQuiz}
        onMarkForRevision={handleMarkForRevision}
        onSubmit={handleSubmitAnswer}
      />
    {:else}
      <StatsPage
        moduleLabel={selectedModuleLabel}
        stats={stats}
        loading={statsLoading}
        reviewOnly={reviewOnly}
        errorMessage={statsError}
        onToggleReviewOnly={handleToggleReviewOnly}
        onOpenCreate={handleOpenCreate}
        onOpenEdit={handleOpenEdit}
      />
    {/if}
  </main>

  <EditorDrawer
    open={editorOpen}
    modules={modules}
    editingQuestion={editingQuestion}
    saving={savingQuestion}
    onClose={() => (editorOpen = false)}
    onCreateModule={handleCreateModule}
    onSave={handleSaveQuestion}
  />
</div>
