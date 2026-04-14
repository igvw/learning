import type { QuestionImportResult, QuestionImportReviewRow, QuestionImportRowPayload } from './types';

export function cloneImportRows(rows: QuestionImportRowPayload[]): QuestionImportRowPayload[] {
  return rows.map((row) => ({
    row_number: row.row_number,
    qml_line: row.qml_line
  }));
}

export function reviewRowDraftQmlLine(row: QuestionImportReviewRow): string {
  if ((row.status === 'duplicate' || row.status === 'relocation') && row.matched_questions.length > 0 && row.matched_questions[0]?.qml_line) {
    return row.matched_questions[0].qml_line;
  }
  return row.qml_line;
}

export function draftImportRowsFromResult(result: QuestionImportResult): QuestionImportRowPayload[] {
  const editableReviewRowLines = new Map(
    result.review_rows.filter((row) => row.editable).map((row) => [row.row_number, reviewRowDraftQmlLine(row)])
  );

  return cloneImportRows(
    result.rows.map((row) => ({
      row_number: row.row_number,
      qml_line: editableReviewRowLines.get(row.row_number) ?? row.qml_line
    }))
  ).sort((left, right) => left.row_number - right.row_number);
}

export function currentImportRowValue(
  rows: QuestionImportRowPayload[],
  rowNumber: number,
  fallback: string
): string {
  return rows.find((row) => row.row_number === rowNumber)?.qml_line ?? fallback;
}

export function sameImportRows(left: QuestionImportRowPayload[], right: QuestionImportRowPayload[]): boolean {
  if (left.length !== right.length) {
    return false;
  }
  return left.every((row, index) => row.row_number === right[index].row_number && row.qml_line === right[index].qml_line);
}
