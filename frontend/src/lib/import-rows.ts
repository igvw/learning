import type { QuestionImportResult, QuestionImportReviewRow, QuestionImportRowPayload } from './types';

export function cloneImportRows(rows: QuestionImportRowPayload[]): QuestionImportRowPayload[] {
  return rows.map((row) => ({
    start_line: row.start_line,
    end_line: row.end_line,
    entry_kind: row.entry_kind,
    qml_text: row.qml_text
  }));
}

export function reviewRowDraftQmlText(row: QuestionImportReviewRow): string {
  if ((row.status === 'duplicate' || row.status === 'relocation') && row.matched_questions.length > 0 && row.matched_questions[0]?.qml_text) {
    return row.matched_questions[0].qml_text;
  }
  return row.qml_text;
}

export function draftImportRowsFromResult(result: QuestionImportResult): QuestionImportRowPayload[] {
  const editableReviewRowLines = new Map(
    result.review_rows.filter((row) => row.editable).map((row) => [row.start_line, reviewRowDraftQmlText(row)])
  );

  return cloneImportRows(
    result.rows.map((row) => ({
      start_line: row.start_line,
      end_line: row.end_line,
      entry_kind: row.entry_kind,
      qml_text: editableReviewRowLines.get(row.start_line) ?? row.qml_text
    }))
  ).sort((left, right) => left.start_line - right.start_line);
}

export function currentImportRowValue(
  rows: QuestionImportRowPayload[],
  startLine: number,
  fallback: string
): string {
  return rows.find((row) => row.start_line === startLine)?.qml_text ?? fallback;
}

export function sameImportRows(left: QuestionImportRowPayload[], right: QuestionImportRowPayload[]): boolean {
  if (left.length !== right.length) {
    return false;
  }
  return left.every(
    (row, index) =>
      row.start_line === right[index].start_line &&
      row.end_line === right[index].end_line &&
      row.entry_kind === right[index].entry_kind &&
      row.qml_text === right[index].qml_text
  );
}
