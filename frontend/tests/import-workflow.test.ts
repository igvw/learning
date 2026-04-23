import { describe, expect, it, vi } from 'vitest';

import { buildImportResult, buildImportReviewRow, buildImportRow } from './builders';
import {
  commitImportInChunks,
  prepareImportSave,
  rebuildImportStateAfterPartialSave
} from '../src/lib/import-workflow';

describe('import-workflow helpers', () => {
  it('prepares a blocked save with a validation status and no queue', async () => {
    const rows = [buildImportRow()];
    const validated = buildImportResult({
      rows,
      review_rows: [buildImportReviewRow({ status: 'invalid', blocking: true, matched_questions: [] })]
    });
    const validateRows = vi.fn().mockResolvedValue(validated);

    const prepared = await prepareImportSave({
      moduleId: 3,
      rows,
      validateRows
    });

    expect(validateRows).toHaveBeenCalledWith(3, rows);
    expect(prepared.queue).toEqual([]);
    expect(prepared.saveStatus).toEqual({
      message: 'Fix the highlighted rows before saving.',
      tone: 'error'
    });
  });

  it('commits rows in chunks and reports progress', async () => {
    const rows = [
      buildImportRow({ start_line: 1, end_line: 1, entry_kind: 'plain', qml_text: 'one [1]' }),
      buildImportRow({ start_line: 2, end_line: 2, entry_kind: 'plain', qml_text: 'two [2]' }),
      buildImportRow({ start_line: 3, end_line: 3, entry_kind: 'plain', qml_text: 'three [3]' })
    ];
    const progress: Array<{ completed: number; total: number }> = [];
    const commitRows = vi
      .fn()
      .mockResolvedValueOnce(buildImportResult({ committed: true, committed_count: 2 }))
      .mockResolvedValueOnce(buildImportResult({ committed: true, committed_count: 1 }));

    const result = await commitImportInChunks({
      moduleId: 3,
      rows,
      commitRows,
      chunkSize: 2,
      onProgress: (next) => progress.push(next)
    });

    expect(commitRows).toHaveBeenNthCalledWith(1, 3, rows.slice(0, 2));
    expect(commitRows).toHaveBeenNthCalledWith(2, 3, rows.slice(2, 3));
    expect(result).toEqual({
      completed: true,
      committedRows: 3,
      remainingRows: []
    });
    expect(progress).toEqual([
      { completed: 0, total: 3 },
      { completed: 2, total: 3 },
      { completed: 3, total: 3 }
    ]);
  });

  it('rebuilds the remaining import state after a partial save', async () => {
    const remainingRows = [buildImportRow({ start_line: 11, end_line: 11, entry_kind: 'plain', qml_text: 'elleve [eleven]' })];
    const validated = buildImportResult({
      rows: remainingRows,
      valid_row_count: 0,
      review_rows: [buildImportReviewRow({ start_line: 11, end_line: 11, status: 'invalid', blocking: true, matched_questions: [] })]
    });
    const validateRows = vi.fn().mockResolvedValue(validated);

    const rebuilt = await rebuildImportStateAfterPartialSave({
      moduleId: 3,
      rows: remainingRows,
      committedRows: 10,
      validateRows
    });

    expect(validateRows).toHaveBeenCalledWith(3, remainingRows);
    expect(rebuilt.draftRows).toEqual(remainingRows);
    expect(rebuilt.saveStatus).toEqual({
      message: 'Saved 10 rows. Fix the highlighted rows to continue.',
      tone: 'error'
    });
  });
});
