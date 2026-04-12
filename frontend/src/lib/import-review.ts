import type { QuestionImportResult, QuestionImportReviewRow, QuestionImportRowPayload } from './types';
import { cloneImportRows } from './import-session';

export type AnswerChoice = {
  key: string;
  text: string;
  blockIndex: number;
  sources: Array<'current' | 'new' | 'manual'>;
};

export function parsePendingImportRows(value: string): QuestionImportRowPayload[] {
  return value
    .split(/\r?\n/)
    .map((qmlLine, index) => ({ row_number: index + 1, qml_line: qmlLine }))
    .filter((row) => row.qml_line.trim());
}

export function effectiveImportRowsFromResult(result: QuestionImportResult): QuestionImportRowPayload[] {
  const editableReviewRowLines = new Map(
    result.review_rows
      .filter((row) => row.editable)
      .map((row) => {
        const currentQmlLine =
          (row.status === 'duplicate' || row.status === 'relocation') && row.matched_questions.length > 0
            ? row.matched_questions[0].qml_line
            : row.qml_line;
        return [row.row_number, currentQmlLine];
      })
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

export function reviewRowsForPendingRows(
  result: QuestionImportResult | null,
  pendingRows: QuestionImportRowPayload[]
): QuestionImportReviewRow[] {
  return result?.review_rows.filter((row) => pendingRows.some((pendingRow) => pendingRow.row_number === row.row_number)) ?? [];
}

function referenceAnswerBlocks(row: QuestionImportReviewRow): string[] {
  if (row.current_answer_blocks.length > 0) {
    return row.current_answer_blocks;
  }
  return row.matched_questions.flatMap((question) => question.answer_blocks);
}

function splitAnswerAlternatives(block: string): string[] {
  return block
    .split('|')
    .map((value) => value.trim())
    .filter(Boolean);
}

function answerGroupsFromBlocks(blocks: string[]): string[][] {
  return blocks.map((block) => splitAnswerAlternatives(block));
}

function answerRanges(qmlLine: string): Array<{ start: number; end: number; content: string }> {
  const ranges: Array<{ start: number; end: number; content: string }> = [];
  const stack: Array<{ open: '[' | '{'; index: number }> = [];
  for (let index = 0; index < qmlLine.length; index += 1) {
    const char = qmlLine[index];
    if (char === '[' || char === '{') {
      stack.push({ open: char, index });
      continue;
    }
    if (char === ']' || char === '}') {
      const expectedOpen = char === ']' ? '[' : '{';
      const candidate = stack.pop();
      if (!candidate || candidate.open !== expectedOpen) {
        continue;
      }
      ranges.push({
        start: candidate.index,
        end: index,
        content: qmlLine.slice(candidate.index + 1, index)
      });
    }
  }
  return ranges.sort((left, right) => left.start - right.start);
}

function qmlAnswerGroups(qmlLine: string): string[][] {
  const ranges = answerRanges(qmlLine);
  if (ranges.length === 0) {
    return [];
  }
  if (ranges.length === 1) {
    return ranges[0].content.split(',').map((group) => splitAnswerAlternatives(group));
  }
  return ranges.map((range) => splitAnswerAlternatives(range.content));
}

export function answerChoicesByBlock(row: QuestionImportReviewRow, qmlLine: string = row.qml_line): AnswerChoice[][] {
  const currentGroups = answerGroupsFromBlocks(referenceAnswerBlocks(row));
  const newGroups = answerGroupsFromBlocks(row.imported_answer_blocks);
  const qmlGroups = qmlAnswerGroups(qmlLine);
  const totalBlocks = Math.max(currentGroups.length, newGroups.length, qmlGroups.length);

  return Array.from({ length: totalBlocks }, (_, blockIndex) => {
    const choicesByText = new Map<string, { text: string; sources: Set<'current' | 'new' | 'manual'> }>();
    const orderedTexts: string[] = [];

    function registerChoice(text: string, source: 'current' | 'new' | 'manual'): void {
      const normalizedText = text.trim();
      if (!normalizedText) {
        return;
      }
      let choice = choicesByText.get(normalizedText);
      if (!choice) {
        choice = {
          text: normalizedText,
          sources: new Set()
        };
        choicesByText.set(normalizedText, choice);
        orderedTexts.push(normalizedText);
      }
      choice.sources.add(source);
    }

    for (const answer of currentGroups[blockIndex] ?? []) {
      registerChoice(answer, 'current');
    }
    for (const answer of newGroups[blockIndex] ?? []) {
      registerChoice(answer, 'new');
    }
    for (const answer of qmlGroups[blockIndex] ?? []) {
      const normalizedAnswer = answer.trim();
      if (!normalizedAnswer) {
        continue;
      }
      if (!choicesByText.has(normalizedAnswer)) {
        registerChoice(normalizedAnswer, 'manual');
      }
    }

    return orderedTexts.map((text, optionIndex) => ({
      key: `${blockIndex}:${optionIndex}:${text}`,
      text,
      blockIndex,
      sources: Array.from(choicesByText.get(text)?.sources ?? [])
    }));
  });
}

function toggleAnswerInGroup(group: string, answerText: string): string {
  const normalizedAnswer = answerText.trim();
  if (!normalizedAnswer) {
    return group.trim();
  }

  const existing = splitAnswerAlternatives(group);
  if (existing.some((value) => value === normalizedAnswer)) {
    return existing.filter((value) => value !== normalizedAnswer).join(' | ');
  }
  if (existing.length === 0) {
    return normalizedAnswer;
  }
  return `${existing.join(' | ')} | ${normalizedAnswer}`;
}

export function answerSelectedInQmlLine(qmlLine: string, blockIndex: number, answerText: string): boolean {
  const normalizedAnswer = answerText.trim();
  if (!normalizedAnswer) {
    return false;
  }

  const ranges = answerRanges(qmlLine);
  if (ranges.length === 0) {
    return false;
  }

  const targetRange = ranges.length === 1 ? ranges[0] : ranges[Math.min(blockIndex, ranges.length - 1)];
  const groupIndex = ranges.length === 1 ? blockIndex : 0;
  const groups = targetRange.content
    .split(',')
    .map((value) => value.trim());

  if (groupIndex >= groups.length) {
    return false;
  }

  return splitAnswerAlternatives(groups[groupIndex]).some((value) => value === normalizedAnswer);
}

export function toggleAnswerInQmlLine(qmlLine: string, blockIndex: number, answerText: string): string {
  const normalizedAnswer = answerText.trim();
  if (!normalizedAnswer) {
    return qmlLine;
  }

  const ranges = answerRanges(qmlLine);
  if (ranges.length === 0) {
    return `${qmlLine.trim()} [${normalizedAnswer}]`;
  }

  const targetRange = ranges.length === 1 ? ranges[0] : ranges[Math.min(blockIndex, ranges.length - 1)];
  const groupIndex = ranges.length === 1 ? blockIndex : 0;
  const groups = targetRange.content
    .split(',')
    .map((value) => value.trim());

  while (groups.length < groupIndex) {
    groups.push('');
  }

  if (groupIndex < groups.length) {
    groups[groupIndex] = toggleAnswerInGroup(groups[groupIndex], normalizedAnswer);
  } else {
    groups.push(normalizedAnswer);
  }

  return `${qmlLine.slice(0, targetRange.start + 1)}${groups.join(', ')}${qmlLine.slice(targetRange.end)}`;
}

export function answerChoiceSourceClass(choice: AnswerChoice): string {
  const sources = new Set(choice.sources);
  if (sources.has('current') && sources.has('new')) {
    return 'source-current-new';
  }
  if (sources.has('current')) {
    return 'source-current';
  }
  if (sources.has('new')) {
    return 'source-new';
  }
  return 'source-manual';
}

export function answerChoiceSourceLabel(choice: AnswerChoice): string {
  const sources = new Set(choice.sources);
  if (sources.has('current') && sources.has('new')) {
    return 'Current and imported answer';
  }
  if (sources.has('current')) {
    return 'Current answer';
  }
  if (sources.has('new')) {
    return 'Imported answer';
  }
  return 'Manual answer';
}
