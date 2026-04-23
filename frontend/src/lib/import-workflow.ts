import { cloneImportRows } from './import-rows';
import {
  IMPORT_COMMIT_CHUNK_SIZE,
  importCommitQueue,
  partialSaveStatus,
  removeCommittedImportRows,
  rowChunks,
  type ImportSaveStatus,
  validationSaveStatus
} from './import-session';
import type { QuestionImportResult, QuestionImportRowPayload } from './types';

export interface ImportSavePreparation {
  validatedState: QuestionImportResult;
  draftRows: QuestionImportRowPayload[];
  queue: QuestionImportRowPayload[];
  saveStatus: ImportSaveStatus | null;
}

export async function prepareImportSave({
  moduleId,
  rows,
  validateRows
}: {
  moduleId: number;
  rows: QuestionImportRowPayload[];
  validateRows: (moduleId: number, rows: QuestionImportRowPayload[]) => Promise<QuestionImportResult>;
}): Promise<ImportSavePreparation> {
  const validatedState = await validateRows(moduleId, rows);
  return {
    validatedState,
    draftRows: cloneImportRows(rows),
    queue: importCommitQueue(rows, validatedState),
    saveStatus: validationSaveStatus(validatedState)
  };
}

export interface ImportChunkCommitProgress {
  completed: number;
  total: number;
}

export interface ImportChunkCommitResult {
  completed: boolean;
  committedRows: number;
  remainingRows: QuestionImportRowPayload[];
}

export async function commitImportInChunks({
  moduleId,
  rows,
  commitRows,
  chunkSize = IMPORT_COMMIT_CHUNK_SIZE,
  onProgress
}: {
  moduleId: number;
  rows: QuestionImportRowPayload[];
  commitRows: (moduleId: number, rows: QuestionImportRowPayload[]) => Promise<QuestionImportResult>;
  chunkSize?: number;
  onProgress?: (progress: ImportChunkCommitProgress) => void;
}): Promise<ImportChunkCommitResult> {
  const total = rows.length;
  let committedRows = 0;
  let remainingRows = cloneImportRows(rows);

  onProgress?.({ completed: committedRows, total });
  for (const chunk of rowChunks(rows, chunkSize)) {
    const nextState = await commitRows(moduleId, chunk);
    if (!nextState.committed) {
      return {
        completed: false,
        committedRows,
        remainingRows
      };
    }

    committedRows += nextState.committed_count;
    onProgress?.({ completed: committedRows, total });

    const committedStartLines = new Set(chunk.map((row) => row.start_line));
    remainingRows = removeCommittedImportRows(remainingRows, committedStartLines);
  }

  return {
    completed: true,
    committedRows,
    remainingRows
  };
}

export async function rebuildImportStateAfterPartialSave({
  moduleId,
  rows,
  committedRows,
  validateRows
}: {
  moduleId: number;
  rows: QuestionImportRowPayload[];
  committedRows: number;
  validateRows: (moduleId: number, rows: QuestionImportRowPayload[]) => Promise<QuestionImportResult>;
}): Promise<{
  validatedState: QuestionImportResult;
  draftRows: QuestionImportRowPayload[];
  saveStatus: ImportSaveStatus;
}> {
  const validatedState = await validateRows(moduleId, rows);
  return {
    validatedState,
    draftRows: cloneImportRows(rows),
    saveStatus: partialSaveStatus(validatedState, committedRows)
  };
}
