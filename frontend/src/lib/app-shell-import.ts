import {
  clearImportSessionStorage,
  persistImportSession,
  restoreImportSession
} from './app-state';
import { cloneImportRows } from './import-rows';
import type { ModuleNode, QuestionImportResult, QuestionImportRowPayload } from './types';

export type ImportStatusTone = 'error' | 'info' | '';
export type ImportHeaderTone = 'progress' | 'error' | 'info';

export interface ImportUiState {
  open: boolean;
  targetModuleId: number | null;
  result: QuestionImportResult | null;
  busy: boolean;
  error: string;
  draftQmlText: string;
  draftRows: QuestionImportRowPayload[];
  saveStatusMessage: string;
  saveStatusTone: ImportStatusTone;
  saveProgressTotal: number;
  saveProgressCompleted: number;
  sessionReady: boolean;
}

export interface ImportStatusSummary {
  visible: boolean;
  tone: ImportHeaderTone;
  label: string;
  detail: string;
}

export function initialImportUiState(): ImportUiState {
  return {
    open: false,
    targetModuleId: null,
    result: null,
    busy: false,
    error: '',
    draftQmlText: '',
    draftRows: [],
    saveStatusMessage: '',
    saveStatusTone: '',
    saveProgressTotal: 0,
    saveProgressCompleted: 0,
    sessionReady: false
  };
}

export function resetImportUiState(state: ImportUiState, closeDrawer = false): ImportUiState {
  return {
    ...state,
    open: closeDrawer ? false : state.open,
    targetModuleId: closeDrawer ? null : state.targetModuleId,
    result: null,
    busy: false,
    error: '',
    draftQmlText: '',
    draftRows: [],
    saveStatusMessage: '',
    saveStatusTone: '',
    saveProgressTotal: 0,
    saveProgressCompleted: 0
  };
}

export function closeImportUiState(state: ImportUiState): ImportUiState {
  if (state.busy) {
    return {
      ...state,
      open: false
    };
  }
  return resetImportUiState(state, true);
}

export function reopenImportUiState(state: ImportUiState): ImportUiState {
  if (state.targetModuleId === null) {
    return state;
  }
  return {
    ...state,
    open: true
  };
}

export function openImportUiForModule(state: ImportUiState, moduleId: number): ImportUiState {
  if (state.busy && state.targetModuleId !== null) {
    return {
      ...state,
      open: true
    };
  }

  return {
    ...resetImportUiState(state),
    open: true,
    targetModuleId: moduleId
  };
}

export function updateImportUiDraft(
  state: ImportUiState,
  qmlText: string,
  rows: QuestionImportRowPayload[]
): ImportUiState {
  return {
    ...state,
    draftQmlText: qmlText,
    draftRows: cloneImportRows(rows)
  };
}

export function setImportUiSaveStatus(
  state: ImportUiState,
  message = '',
  tone: ImportStatusTone = ''
): ImportUiState {
  return {
    ...state,
    saveStatusMessage: message,
    saveStatusTone: tone
  };
}

export function restoreImportUiStateFromSession({
  state,
  storage,
  instanceKey,
  modules
}: {
  state: ImportUiState;
  storage: Storage;
  instanceKey: string;
  modules: ModuleNode[];
}): ImportUiState {
  const restored = restoreImportSession(storage, {
    instanceKey,
    modules
  });

  const resetState = resetImportUiState(state, true);
  if (!restored) {
    clearImportSessionStorage(storage, instanceKey);
    return resetState;
  }

  return {
    ...resetState,
    open: true,
    targetModuleId: restored.targetModuleId,
    draftQmlText: restored.qmlText,
    draftRows: cloneImportRows(restored.rows),
    result: restored.result
  };
}

export function persistImportUiState({
  storage,
  instanceKey,
  modules,
  state
}: {
  storage: Storage;
  instanceKey: string;
  modules: ModuleNode[];
  state: ImportUiState;
}): void {
  persistImportSession(storage, {
    instanceKey,
    modules,
    open: state.open,
    targetModuleId: state.targetModuleId,
    qmlText: state.draftQmlText,
    rows: state.draftRows,
    result: state.result
  });
}

export function importStatusSummary(state: ImportUiState): ImportStatusSummary {
  const visible =
    state.targetModuleId !== null &&
    !state.open &&
    (state.busy || Boolean(state.error) || Boolean(state.saveStatusMessage));

  const tone: ImportHeaderTone = state.busy ? 'progress' : state.error || state.saveStatusTone === 'error' ? 'error' : 'info';
  const label = (() => {
    if (state.busy && state.saveProgressTotal > 0) {
      return `Uploading ${state.saveProgressCompleted}/${state.saveProgressTotal}`;
    }
    if (state.busy) {
      return state.result ? 'Saving import...' : 'Preparing import...';
    }
    if (state.error) {
      return 'Import failed';
    }
    return state.saveStatusTone === 'error' ? 'Import needs attention' : 'Import updated';
  })();

  return {
    visible,
    tone,
    label,
    detail: state.error || state.saveStatusMessage || label
  };
}
