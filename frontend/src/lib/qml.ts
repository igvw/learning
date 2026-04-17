import type { QuestionType } from './types';

export interface ParsedQmlQuestion {
  prompt: string;
  question_type: QuestionType;
  accepted_answers: string[][];
  segments: string[];
}

export class QmlError extends Error {}

function splitEscaped(text: string, separator: string): string[] {
  const parts: string[] = [];
  let current = '';
  let escape = false;
  for (const char of text) {
    if (escape) {
      current += char;
      escape = false;
      continue;
    }
    if (char === '\\') {
      escape = true;
      continue;
    }
    if (char === separator) {
      parts.push(current);
      current = '';
      continue;
    }
    current += char;
  }
  if (escape) {
    throw new QmlError('Dangling escape sequence.');
  }
  parts.push(current);
  return parts;
}

function escapeQmlText(text: string): string {
  return text.replace(/\\/g, '\\\\').replace(/([\[\]\{\}\|,])/g, '\\$1');
}

function parseAnswerGroup(text: string): string[] {
  const answers = splitEscaped(text, '|')
    .map((value) => value.trim())
    .filter(Boolean);
  if (answers.length === 0) {
    throw new QmlError('Each answer slot needs at least one accepted answer.');
  }
  return answers;
}

function containsVariableBinding(text: string): boolean {
  return /\$[A-Za-z_][A-Za-z0-9_]*\s*=/.test(text);
}

function findTrailingBox(line: string): { start: number; opening: '[' | '{'; content: string } | null {
  const stripped = line.trimEnd();
  const closing = stripped[stripped.length - 1];
  if (closing !== ']' && closing !== '}') {
    return null;
  }
  const opening = closing === ']' ? '[' : '{';
  let depth = 0;
  let escape = false;
  let start = -1;
  for (let index = 0; index < stripped.length; index += 1) {
    const char = stripped[index];
    if (escape) {
      escape = false;
      continue;
    }
    if (char === '\\') {
      escape = true;
      continue;
    }
    if (char === opening) {
      if (depth === 0) {
        start = index;
      }
      depth += 1;
    } else if (char === closing) {
      depth -= 1;
      if (depth < 0) {
        throw new QmlError('Malformed answer box.');
      }
      if (depth === 0 && index === stripped.length - 1 && start >= 0) {
        return { start, opening, content: stripped.slice(start + 1, index) };
      }
    }
  }
  return null;
}

function parseInlineCloze(line: string): ParsedQmlQuestion {
  const segments: string[] = [];
  const accepted_answers: string[][] = [];
  let currentSegment = '';
  let currentGroup = '';
  let inGroup = false;
  let escape = false;
  let sawGroup = false;

  for (const char of line) {
    if (escape) {
      if (inGroup) {
        currentGroup += char;
      } else {
        currentSegment += char;
      }
      escape = false;
      continue;
    }
    if (char === '\\') {
      escape = true;
      continue;
    }
    if (!inGroup) {
      if (char === '[') {
        segments.push(currentSegment);
        currentSegment = '';
        currentGroup = '';
        inGroup = true;
        sawGroup = true;
        continue;
      }
      if (char === ']') {
        throw new QmlError('Malformed inline cloze question.');
      }
      currentSegment += char;
      continue;
    }
    if (char === ']') {
      accepted_answers.push(parseAnswerGroup(currentGroup));
      inGroup = false;
      continue;
    }
    currentGroup += char;
  }

  if (escape || inGroup || !sawGroup) {
    throw new QmlError('Malformed inline cloze question.');
  }

  segments.push(currentSegment);
  return {
    prompt: segments.join('[_]'),
    question_type: 'inline_cloze',
    accepted_answers,
    segments
  };
}

export function parseQmlLine(line: string): ParsedQmlQuestion {
  const source = line.trim();
  if (!source) {
    throw new QmlError('Question lines cannot be blank.');
  }

  const trailingBox = findTrailingBox(source);
  if (trailingBox) {
    const prompt = source.slice(0, trailingBox.start).trimEnd();
    if (!prompt) {
      throw new QmlError('Prompt is required.');
    }
    if (trailingBox.opening === '{') {
      const slots = splitEscaped(trailingBox.content, ',')
        .map((value) => value.trim())
        .filter(Boolean)
        .map(parseAnswerGroup);
      if (slots.length < 2) {
        throw new QmlError('Unordered questions need at least two answer slots.');
      }
      return {
        prompt,
        question_type: 'multi_text',
        accepted_answers: slots,
        segments: []
      };
    }
    const orderedSlots = splitEscaped(trailingBox.content, ',')
      .map((value) => value.trim())
      .filter(Boolean);
    if (orderedSlots.length > 1) {
      return {
        prompt,
        question_type: 'ordered_multi',
        accepted_answers: orderedSlots.map(parseAnswerGroup),
        segments: []
      };
    }
    return {
      prompt,
      question_type: containsVariableBinding(prompt) ? 'computed_text' : 'single_text',
      accepted_answers: [parseAnswerGroup(trailingBox.content.trim())],
      segments: []
    };
  }

  return parseInlineCloze(source);
}

export function buildQmlLine(question: ParsedQmlQuestion): string {
  if (question.question_type === 'single_text' || question.question_type === 'computed_text') {
    return `${question.prompt.trim()} [${question.accepted_answers[0].map(escapeQmlText).join(' | ')}]`;
  }
  if (question.question_type === 'multi_text') {
    const content = question.accepted_answers.map((group) => group.map(escapeQmlText).join(' | ')).join(', ');
    return `${question.prompt.trim()} {${content}}`;
  }
  if (question.question_type === 'ordered_multi') {
    const content = question.accepted_answers.map((group) => group.map(escapeQmlText).join(' | ')).join(', ');
    return `${question.prompt.trim()} [${content}]`;
  }

  return question.accepted_answers.reduce((line, group, index) => {
    const segment = question.segments[index] ?? '';
    return `${line}${segment}[${group.map(escapeQmlText).join(' | ')}]`;
  }, '') + (question.segments[question.segments.length - 1] ?? '');
}
