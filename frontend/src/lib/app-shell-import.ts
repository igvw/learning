import { cloneImportRows } from './import-rows';
import type { QuestionImportResult, QuestionImportRowPayload } from './types';

export type ImportStatusTone = 'error' | 'info' | '';

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
    saveProgressCompleted: 0
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
    return state;
  }
  return resetImportUiState(state, true);
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
