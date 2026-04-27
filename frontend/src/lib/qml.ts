import type { QuestionType } from './types';

export interface ParsedQmlQuestion {
  prompt: string;
  question_type: QuestionType;
  accepted_answers: string[][];
  segments: string[];
  bundle_qml?: string | null;
}

export interface BundleVariant {
  prompt_values: string[];
  accepted_answers: string[];
}

export interface ParsedBundleEditor {
  template: string;
  variants: BundleVariant[];
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
    segments,
    bundle_qml: null
  };
}

function splitBundleLines(qmlText: string): string[] {
  const lines = qmlText
    .split(/\r?\n/)
    .map((line) => line.trimEnd())
    .filter((line) => line.trim());
  if (lines.length === 0) {
    throw new QmlError('Bundle must include at least one template line.');
  }
  return lines;
}

function stripBundleOuterWrapper(qmlText: string): string[] {
  const lines = splitBundleLines(qmlText);
  const first = lines[0].trimStart();
  if (!first.startsWith('{')) {
    throw new QmlError('Bundle must start with {.');
  }
  lines[0] = first.slice(1);
  if (!lines[lines.length - 1].trimEnd().endsWith('}')) {
    throw new QmlError('Bundle must end with }.');
  }
  const last = lines[lines.length - 1].trimEnd();
  lines[lines.length - 1] = last.slice(0, last.lastIndexOf('}'));
  const cleaned = lines.map((line) => line.trim()).filter(Boolean);
  if (cleaned.length < 2) {
    throw new QmlError('Bundle must include a template and at least one row.');
  }
  return cleaned;
}

function parseBundleTemplateSignature(content: string): { segments: string[]; promptValues: string[]; answerValues: string[] } {
  const stripped = content.trim();
  if (!stripped) {
    throw new QmlError('Bundle template is required.');
  }

  const segments: string[] = [];
  const promptValues: string[] = [];
  let currentSegment = '';
  let answerValues: string[] | null = null;
  let index = 0;
  let escape = false;

  while (index < stripped.length) {
    const char = stripped[index];
    if (escape) {
      currentSegment += char;
      escape = false;
      index += 1;
      continue;
    }
    if (char === '\\') {
      escape = true;
      index += 1;
      continue;
    }
    if (char === '{') {
      let end = index + 1;
      let cell = '';
      let cellEscape = false;
      while (end < stripped.length) {
        const inner = stripped[end];
        if (cellEscape) {
          cell += inner;
          cellEscape = false;
          end += 1;
          continue;
        }
        if (inner === '\\') {
          cellEscape = true;
          end += 1;
          continue;
        }
        if (inner === '}') {
          break;
        }
        cell += inner;
        end += 1;
      }
      if (end >= stripped.length || stripped[end] !== '}') {
        throw new QmlError('Malformed bundle prompt cell.');
      }
      segments.push(currentSegment);
      currentSegment = '';
      promptValues.push(cell.trim());
      index = end + 1;
      continue;
    }
    if (char === '[') {
      let end = index + 1;
      let cell = '';
      let cellEscape = false;
      while (end < stripped.length) {
        const inner = stripped[end];
        if (cellEscape) {
          cell += inner;
          cellEscape = false;
          end += 1;
          continue;
        }
        if (inner === '\\') {
          cellEscape = true;
          end += 1;
          continue;
        }
        if (inner === ']') {
          break;
        }
        cell += inner;
        end += 1;
      }
      if (end >= stripped.length || stripped[end] !== ']') {
        throw new QmlError('Malformed bundle answer slot.');
      }
      answerValues = cell.trim() ? parseAnswerGroup(cell) : [];
      segments.push(currentSegment);
      if (stripped.slice(end + 1).trim()) {
        throw new QmlError('Bundle answer slot must be the final element in the template.');
      }
      currentSegment = '';
      break;
    }
    currentSegment += char;
    index += 1;
  }

  if (answerValues === null) {
    throw new QmlError('Bundle template must end with one answer slot [].');
  }
  if (promptValues.length === 0 && !segments[0]?.trim()) {
    throw new QmlError('Bundle template needs a real prompt.');
  }
  return { segments, promptValues, answerValues };
}

function bundleTemplateFromSegments(segments: string[]): string {
  const parts: string[] = [];
  for (let index = 0; index < segments.length - 1; index += 1) {
    parts.push(segments[index], '{}');
  }
  parts.push(segments[segments.length - 1] ?? '');
  return `${parts.join('').trim()} []`;
}

function parseBundleVariantRow(line: string, promptValueCount: number): { prompt_values: string[]; accepted_answers: string[] } {
  const stripped = line.trim();
  let index = 0;
  const prompt_values: string[] = [];

  for (let count = 0; count < promptValueCount; count += 1) {
    while (index < stripped.length && /\s/.test(stripped[index])) {
      index += 1;
    }
    if (index >= stripped.length || stripped[index] !== '{') {
      throw new QmlError('Bundle row is missing a prompt-value cell.');
    }
    let end = index + 1;
    let cell = '';
    let escape = false;
    while (end < stripped.length) {
      const char = stripped[end];
      if (escape) {
        cell += char;
        escape = false;
        end += 1;
        continue;
      }
      if (char === '\\') {
        escape = true;
        end += 1;
        continue;
      }
      if (char === '}') {
        break;
      }
      cell += char;
      end += 1;
    }
    if (end >= stripped.length || stripped[end] !== '}') {
      throw new QmlError('Malformed bundle prompt-value cell.');
    }
    prompt_values.push(cell.trim());
    index = end + 1;
  }

  while (index < stripped.length && /\s/.test(stripped[index])) {
    index += 1;
  }
  if (index >= stripped.length || stripped[index] !== '[') {
    throw new QmlError('Bundle row must end with an answer cell.');
  }
  let end = index + 1;
  let answerCell = '';
  let escape = false;
  while (end < stripped.length) {
    const char = stripped[end];
    if (escape) {
      answerCell += char;
      escape = false;
      end += 1;
      continue;
    }
    if (char === '\\') {
      escape = true;
      end += 1;
      continue;
    }
    if (char === ']') {
      break;
    }
    answerCell += char;
    end += 1;
  }
  if (end >= stripped.length || stripped[end] !== ']') {
    throw new QmlError('Malformed bundle answer cell.');
  }
  if (stripped.slice(end + 1).trim()) {
    throw new QmlError('Bundle rows may only contain prompt values followed by one answer cell.');
  }
  return { prompt_values, accepted_answers: parseAnswerGroup(answerCell) };
}

export function countBundlePromptValues(prompt: string): number {
  return prompt.split('{}').length - 1;
}

export function buildBundleEditorText(prompt: string, variants: BundleVariant[]): string {
  const lines = [prompt.trim()];
  for (const variant of variants) {
    const promptCells = variant.prompt_values.map((value) => `{${escapeQmlText(value)}}`).join(' ');
    const answerCell = `[${variant.accepted_answers.map(escapeQmlText).join(' | ')}]`;
    lines.push(` ${[promptCells, answerCell].filter(Boolean).join(' ')}`.trimEnd());
  }
  return lines.join('\n');
}

export function buildBundleQml(prompt: string, variants: BundleVariant[]): string {
  const editorText = buildBundleEditorText(prompt, variants);
  if (!editorText) {
    return '';
  }
  const lines = editorText.split('\n');
  lines[0] = `{${lines[0]}`;
  lines[lines.length - 1] = `${lines[lines.length - 1]}}`;
  return lines.join('\n');
}

export function wrapBundleQml(qmlText: string): string {
  const trimmed = qmlText.trim();
  if (!trimmed) {
    return '';
  }
  if (trimmed.startsWith('{') && trimmed.endsWith('}')) {
    return trimmed;
  }
  const lines = splitBundleLines(trimmed);
  lines[0] = `{${lines[0].trimStart()}`;
  lines[lines.length - 1] = `${lines[lines.length - 1].trimEnd()}}`;
  return lines.join('\n');
}

export function unwrapBundleQml(qmlText: string): string {
  return stripBundleOuterWrapper(qmlText).join('\n');
}

export function parseBundleEditorText(qmlText: string): ParsedBundleEditor {
  const contentLines = stripBundleOuterWrapper(wrapBundleQml(qmlText));
  const templateLine = contentLines[0];
  const variantLines = contentLines.slice(1);
  const { segments, promptValues, answerValues } = parseBundleTemplateSignature(templateLine);
  const template = bundleTemplateFromSegments(segments);
  const inlineFirstExample = promptValues.some((value) => value !== '') || answerValues.length > 0;
  const variants: BundleVariant[] = [];
  if (inlineFirstExample) {
    variants.push({ prompt_values: promptValues, accepted_answers: answerValues });
  }
  const promptValueCount = countBundlePromptValues(template);
  for (const line of variantLines) {
    variants.push(parseBundleVariantRow(line, promptValueCount));
  }
  if (variants.length === 0) {
    throw new QmlError('Bundle must include at least one variant row.');
  }

  return { template, variants };
}

function parseBundleQml(qmlText: string): ParsedQmlQuestion {
  const { template, variants } = parseBundleEditorText(qmlText);
  return {
    prompt: template,
    question_type: 'bundle',
    accepted_answers: [],
    segments: [],
    bundle_qml: buildBundleQml(template, variants)
  };
}

export function canonicalizeBundleEditorText(qmlText: string): string {
  const { template, variants } = parseBundleEditorText(qmlText);
  return buildBundleEditorText(template, variants);
}

export function parseQmlLine(line: string): ParsedQmlQuestion {
  const source = line.trim();
  if (!source) {
    throw new QmlError('Question lines cannot be blank.');
  }
  if (source.startsWith('{')) {
    return parseBundleQml(line);
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
        segments: [],
        bundle_qml: null
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
        segments: [],
        bundle_qml: null
      };
    }
    return {
      prompt,
      question_type: 'single_text',
      accepted_answers: [parseAnswerGroup(trailingBox.content.trim())],
      segments: [],
      bundle_qml: null
    };
  }

  return parseInlineCloze(source);
}

export function buildQmlLine(question: ParsedQmlQuestion): string {
  if (question.question_type === 'bundle') {
    if (!question.bundle_qml?.trim()) {
      throw new QmlError('Bundle questions need canonical bundle QML.');
    }
    return question.bundle_qml.trim();
  }
  if (question.question_type === 'single_text') {
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

  return (
    question.accepted_answers.reduce((line, group, index) => {
      const segment = escapeQmlText(question.segments[index] ?? '');
      return `${line}${segment}[${group.map(escapeQmlText).join(' | ')}]`;
    }, '') + escapeQmlText(question.segments[question.segments.length - 1] ?? '')
  );
}
