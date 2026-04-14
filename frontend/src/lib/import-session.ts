import { cloneImportRows, draftImportRowsFromResult } from './import-rows';
import type { QuestionImportResult, QuestionImportRowPayload } from './types';

export type ImportSaveStatusTone = 'error' | 'info' | '';

export interface ImportSaveStatus {
  message: string;
  tone: ImportSaveStatusTone;
}

export const IMPORT_COMMIT_CHUNK_SIZE = 10;

export function initialImportDraftRows(result: QuestionImportResult): QuestionImportRowPayload[] {
  return draftImportRowsFromResult(result);
}

export function rowChunks(rows: QuestionImportRowPayload[], size: number): QuestionImportRowPayload[][] {
  const chunks: QuestionImportRowPayload[][] = [];
  for (let index = 0; index < rows.length; index += size) {
    chunks.push(rows.slice(index, index + size));
  }
  return chunks;
}

export function importCommitQueue(
  rows: QuestionImportRowPayload[],
  result: QuestionImportResult
): QuestionImportRowPayload[] {
  const committableRows = new Set(result.committable_row_numbers ?? []);
  return rows.filter((row) => committableRows.has(row.row_number));
}

export function removeCommittedImportRows(
  rows: QuestionImportRowPayload[],
  committedRowNumbers: Set<number>
): QuestionImportRowPayload[] {
  return rows.filter((row) => !committedRowNumbers.has(row.row_number));
}

export function validationSaveStatus(result: QuestionImportResult): ImportSaveStatus | null {
  if (result.review_rows.some((row) => row.blocking)) {
    return {
      message: 'Fix the highlighted rows before saving.',
      tone: 'error'
    };
  }
  if (result.valid_row_count > 0) {
    return null;
  }
  if (result.exact_duplicate_count > 0) {
    return {
      message: 'Nothing new to save.',
      tone: 'info'
    };
  }
  return {
    message: 'No importable rows remain.',
    tone: 'error'
  };
}

export function partialSaveStatus(result: QuestionImportResult, committedRows: number): ImportSaveStatus {
  if (result.review_rows.some((row) => row.blocking)) {
    return {
      message: `Saved ${committedRows} rows. Fix the highlighted rows to continue.`,
      tone: 'error'
    };
  }
  if (result.valid_row_count > 0) {
    return {
      message: `Saved ${committedRows} rows. Save again to continue.`,
      tone: 'info'
    };
  }
  if (result.exact_duplicate_count > 0 && result.review_rows.length === 0) {
    return {
      message: `Saved ${committedRows} rows. Nothing else to save.`,
      tone: 'info'
    };
  }
  return {
    message: `Saved ${committedRows} rows. No importable rows remain.`,
    tone: 'info'
  };
}
