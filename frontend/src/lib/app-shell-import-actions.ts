import { setImportUiSaveStatus, resetImportUiState, type ImportUiState } from './app-shell-import';
import { cloneImportRows } from './import-rows';
import { initialImportDraftRows } from './import-session';
import { commitImportInChunks, prepareImportSave, rebuildImportStateAfterPartialSave } from './import-workflow';
import type { AuthActor, ModuleNode, QuestionImportResult, QuestionImportRowPayload } from './types';

export async function startImportUiFlow({
  state,
  actor,
  moduleNode,
  qmlText,
  validateText,
  onStateChange = () => {},
  getState = () => state
}: {
  state: ImportUiState;
  actor: AuthActor | null;
  moduleNode: ModuleNode | null;
  qmlText: string;
  validateText: (moduleId: number, qmlText: string) => Promise<QuestionImportResult>;
  onStateChange?: (state: ImportUiState) => void;
  getState?: () => ImportUiState;
}): Promise<ImportUiState> {
  if (!moduleNode || actor?.role !== 'admin') {
    return state;
  }

  const publishState = (stateToPublish: ImportUiState, preserveUiState = true): ImportUiState => {
    const currentState = getState();
    const nextPublishedState = preserveUiState
      ? {
          ...stateToPublish,
          open: currentState.open,
          targetModuleId: currentState.targetModuleId
        }
      : stateToPublish;
    onStateChange(nextPublishedState);
    return nextPublishedState;
  };

  let nextState: ImportUiState = {
    ...setImportUiSaveStatus(state),
    busy: true,
    error: '',
    draftQmlText: qmlText,
    saveProgressTotal: 0,
    saveProgressCompleted: 0
  };
  nextState = publishState(nextState);

  try {
    const nextResult = await validateText(moduleNode.id, qmlText);
    nextState = {
      ...nextState,
      draftRows: initialImportDraftRows(nextResult),
      result: nextResult
    };
    nextState = publishState(nextState);
  } catch (error) {
    nextState = {
      ...nextState,
      error: error instanceof Error ? error.message : 'Unable to start this import.'
    };
    nextState = publishState(nextState);
  } finally {
    nextState = {
      ...nextState,
      busy: false
    };
    nextState = publishState(nextState);
  }

  return nextState;
}

export async function commitImportUiFlow({
  state,
  actor,
  moduleNode,
  rows,
  validateRows,
  commitRows,
  chunkSize,
  onStateChange = () => {},
  getState = () => state
}: {
  state: ImportUiState;
  actor: AuthActor | null;
  moduleNode: ModuleNode | null;
  rows: QuestionImportRowPayload[];
  validateRows: (moduleId: number, rows: QuestionImportRowPayload[]) => Promise<QuestionImportResult>;
  commitRows: (moduleId: number, rows: QuestionImportRowPayload[]) => Promise<QuestionImportResult>;
  chunkSize: number;
  onStateChange?: (state: ImportUiState) => void;
  getState?: () => ImportUiState;
}): Promise<{ state: ImportUiState; committedAll: boolean }> {
  if (!moduleNode || actor?.role !== 'admin') {
    return { state, committedAll: false };
  }

  const publishState = (stateToPublish: ImportUiState, preserveUiState = true): ImportUiState => {
    const currentState = getState();
    const nextPublishedState = preserveUiState
      ? {
          ...stateToPublish,
          open: currentState.open,
          targetModuleId: currentState.targetModuleId
        }
      : stateToPublish;
    onStateChange(nextPublishedState);
    return nextPublishedState;
  };

  let queuedRows: QuestionImportRowPayload[] = [];
  let nextState: ImportUiState = {
    ...setImportUiSaveStatus(state),
    busy: true,
    error: '',
    draftRows: cloneImportRows(rows)
  };
  nextState = publishState(nextState);

  try {
    const { validatedState, draftRows, queue, saveStatus } = await prepareImportSave({
      moduleId: moduleNode.id,
      rows,
      validateRows
    });
    nextState = {
      ...nextState,
      result: validatedState,
      draftRows
    };
    nextState = publishState(nextState);
    queuedRows = queue;

    const validationStatus =
      saveStatus ?? (queue.length === 0 ? { message: 'Nothing new to save.', tone: 'info' as const } : null);
    if (validationStatus) {
      nextState = {
        ...setImportUiSaveStatus(nextState, validationStatus.message, validationStatus.tone),
        saveProgressTotal: 0,
        saveProgressCompleted: 0,
        busy: false
      };
      nextState = publishState(nextState);
      return {
        state: nextState,
        committedAll: false
      };
    }

    const commitResult = await commitImportInChunks({
      moduleId: moduleNode.id,
      rows: queue,
      commitRows,
      chunkSize,
      onProgress: ({ completed, total }) => {
        nextState = {
          ...nextState,
          saveProgressCompleted: completed,
          saveProgressTotal: total
        };
        nextState = publishState(nextState);
      }
    });
    if (!commitResult.completed) {
      const rebuiltState = await rebuildImportStateAfterPartialSave({
        moduleId: moduleNode.id,
        rows: commitResult.remainingRows,
        committedRows: commitResult.committedRows,
        validateRows
      });
      nextState = {
        ...setImportUiSaveStatus(nextState, rebuiltState.saveStatus.message, rebuiltState.saveStatus.tone),
        draftRows: rebuiltState.draftRows,
        result: rebuiltState.validatedState,
        busy: false,
        saveProgressTotal: 0,
        saveProgressCompleted: 0
      };
      nextState = publishState(nextState);
      return {
        state: nextState,
        committedAll: false
      };
    }

    nextState = resetImportUiState(nextState, true);
    nextState = publishState(nextState, false);
    return {
      state: nextState,
      committedAll: true
    };
  } catch (error) {
    if (nextState.saveProgressCompleted > 0 && queuedRows.length > 0) {
      try {
        const remainingRows = queuedRows.slice(nextState.saveProgressCompleted);
        const rebuiltState = await rebuildImportStateAfterPartialSave({
          moduleId: moduleNode.id,
          rows: remainingRows,
          committedRows: nextState.saveProgressCompleted,
          validateRows
        });
        nextState = {
          ...setImportUiSaveStatus(nextState, rebuiltState.saveStatus.message, rebuiltState.saveStatus.tone),
          draftRows: rebuiltState.draftRows,
          result: rebuiltState.validatedState,
          busy: false,
          saveProgressTotal: 0,
          saveProgressCompleted: 0
        };
        nextState = publishState(nextState);
        return {
          state: nextState,
          committedAll: false
        };
      } catch (rebuildError) {
        console.error(rebuildError);
      }
    }

    nextState = {
      ...nextState,
      error: error instanceof Error ? error.message : 'Unable to commit this upload.',
      busy: false,
      saveProgressTotal: 0,
      saveProgressCompleted: 0
    };
    nextState = publishState(nextState);
    return {
      state: nextState,
      committedAll: false
    };
  }
}
