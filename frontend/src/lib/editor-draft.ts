import {
  buildQmlLine,
  parseBundleEditorText,
  parseQmlLine,
  unwrapBundleQml,
  wrapBundleQml
} from './qml';
import type {
  ModuleNode,
  QuestionDraftPayload,
  QuestionRow,
  QuestionType
} from './types';

export type FlatModule = { id: number; label: string; isLeaf: boolean };
export type MultiSlot = { answersText: string };
export type InlineBlank = { segmentBefore: string; answersText: string };
export type BundleVariantDraft = { promptValues: string[]; answersText: string };

export type EditorState = {
  moduleId: number;
  prompt: string;
  questionType: QuestionType;
  rank: number;
  resetStats: boolean;
  singleAnswersText: string;
  multiSlots: MultiSlot[];
  inlineBlanks: InlineBlank[];
  inlineTail: string;
  bundleTemplate: string;
  bundleVariants: BundleVariantDraft[];
  bundleQml: string;
  qmlText: string;
};

type StructuredDraft = {
  prompt: string;
  question_type: QuestionType;
  accepted_answers: string[][];
  segments: string[];
  bundle_qml?: string | null;
};

export function splitAnswerEditorText(value: string): string[] {
  return value
    .split('|')
    .map((entry) => entry.trim())
    .filter(Boolean);
}

export function joinAnswerEditorText(values: string[]): string {
  return values.join(' | ');
}

export function flattenModules(nodes: ModuleNode[]): FlatModule[] {
  return nodes.flatMap((node) => [
    { id: node.id, label: node.full_slug, isLeaf: node.children.length === 0 },
    ...flattenModules(node.children)
  ]);
}

export function findModuleById(nodes: ModuleNode[], moduleId: number | null): ModuleNode | null {
  if (moduleId === null) {
    return null;
  }
  for (const node of nodes) {
    if (node.id === moduleId) {
      return node;
    }
    const childMatch = findModuleById(node.children, moduleId);
    if (childMatch) {
      return childMatch;
    }
  }
  return null;
}

function findFirstLeafModuleId(nodes: ModuleNode[]): number | null {
  for (const node of nodes) {
    if (node.children.length === 0) {
      return node.id;
    }
    const childLeafId = findFirstLeafModuleId(node.children);
    if (childLeafId !== null) {
      return childLeafId;
    }
  }
  return null;
}

function findFirstLeafInBranch(node: ModuleNode): number | null {
  if (node.children.length === 0) {
    return node.id;
  }
  return findFirstLeafModuleId(node.children);
}

export function defaultCreateModuleId(modules: ModuleNode[], defaultModuleId: number | null): number {
  if (defaultModuleId !== null) {
    const defaultNode = findModuleById(modules, defaultModuleId);
    if (defaultNode) {
      const branchLeafId = findFirstLeafInBranch(defaultNode);
      if (branchLeafId !== null) {
        return branchLeafId;
      }
    }
  }
  return findFirstLeafModuleId(modules) ?? 0;
}

export function buildStructuredDraft(
  state: Pick<
    EditorState,
    | 'prompt'
    | 'questionType'
    | 'singleAnswersText'
    | 'multiSlots'
    | 'inlineBlanks'
    | 'inlineTail'
    | 'bundleQml'
  >
): StructuredDraft {
  if (state.questionType === 'bundle') {
    return {
      prompt: '',
      question_type: 'bundle',
      accepted_answers: [],
      segments: [],
      bundle_qml: state.bundleQml.trim() ? wrapBundleQml(state.bundleQml.trim()) : ''
    };
  }
  if (state.questionType === 'single_text') {
    return {
      prompt: state.prompt.trim(),
      question_type: state.questionType,
      accepted_answers: [splitAnswerEditorText(state.singleAnswersText)],
      segments: []
    };
  }
  if (state.questionType === 'multi_text' || state.questionType === 'ordered_multi') {
    return {
      prompt: state.prompt.trim(),
      question_type: state.questionType,
      accepted_answers: state.multiSlots.map((slot) => splitAnswerEditorText(slot.answersText)),
      segments: []
    };
  }
  return {
    prompt: state.prompt.trim(),
    question_type: state.questionType,
    accepted_answers: state.inlineBlanks.map((blank) => splitAnswerEditorText(blank.answersText)),
    segments: [...state.inlineBlanks.map((blank) => blank.segmentBefore), state.inlineTail]
  };
}

export function parseEditorStateFromQml(
  value: string
): Pick<
  EditorState,
  | 'prompt'
  | 'questionType'
  | 'singleAnswersText'
  | 'multiSlots'
  | 'inlineBlanks'
  | 'inlineTail'
  | 'bundleTemplate'
  | 'bundleVariants'
  | 'bundleQml'
> {
  const parsed = parseQmlLine(value);
  if (parsed.question_type === 'bundle') {
    const bundleQml = unwrapBundleQml(parsed.bundle_qml ?? value);
    const bundle = parseBundleEditorText(bundleQml);
    return {
      prompt: parsed.prompt,
      questionType: 'bundle',
      singleAnswersText: '',
      multiSlots: [],
      inlineBlanks: [],
      inlineTail: '',
      bundleTemplate: bundle.template,
      bundleVariants: bundle.variants.map((variant) => ({
        promptValues: [...variant.prompt_values],
        answersText: joinAnswerEditorText(variant.accepted_answers)
      })),
      bundleQml
    };
  }
  if (parsed.question_type === 'single_text') {
    return {
      prompt: parsed.prompt,
      questionType: parsed.question_type,
      singleAnswersText: joinAnswerEditorText(parsed.accepted_answers[0] ?? []),
      multiSlots: [],
      inlineBlanks: [],
      inlineTail: '',
      bundleTemplate: '',
      bundleVariants: [],
      bundleQml: ''
    };
  }
  if (parsed.question_type === 'multi_text' || parsed.question_type === 'ordered_multi') {
    return {
      prompt: parsed.prompt,
      questionType: parsed.question_type,
      singleAnswersText: '',
      multiSlots: parsed.accepted_answers.map((answers) => ({ answersText: joinAnswerEditorText(answers) })),
      inlineBlanks: [],
      inlineTail: '',
      bundleTemplate: '',
      bundleVariants: [],
      bundleQml: ''
    };
  }
  return {
    prompt: parsed.prompt,
    questionType: parsed.question_type,
    singleAnswersText: '',
    multiSlots: [],
    inlineBlanks: parsed.accepted_answers.map((answers, index) => ({
      segmentBefore: parsed.segments[index] ?? '',
      answersText: joinAnswerEditorText(answers)
    })),
    inlineTail: parsed.segments[parsed.segments.length - 1] ?? '',
    bundleTemplate: '',
    bundleVariants: [],
    bundleQml: ''
  };
}

export function buildEditorState(
  question: QuestionRow | null,
  modules: ModuleNode[],
  defaultModuleIdValue: number | null
): EditorState {
  const moduleId = question?.module_id ?? defaultCreateModuleId(modules, defaultModuleIdValue);
  const prompt = question?.prompt ?? '';
  const questionType = question?.question_type ?? 'single_text';
  const rank = question?.rank ?? 1;
  const resetStats = true;

  let singleAnswersText = '';
  let multiSlots: MultiSlot[] = [];
  let inlineBlanks: InlineBlank[] = [];
  let inlineTail = '';
  let bundleTemplate = '';
  let bundleVariants: BundleVariantDraft[] = [];
  let bundleQml = question?.bundle_qml ? unwrapBundleQml(question.bundle_qml) : '';

  if (questionType === 'bundle') {
    if (bundleQml) {
      const bundle = parseBundleEditorText(bundleQml);
      bundleTemplate = bundle.template;
      bundleVariants = bundle.variants.map((variant) => ({
        promptValues: [...variant.prompt_values],
        answersText: joinAnswerEditorText(variant.accepted_answers)
      }));
    }
  } else if (questionType === 'single_text') {
    singleAnswersText = joinAnswerEditorText(question?.accepted_answers?.[0] ?? []);
  } else if (questionType === 'multi_text' || questionType === 'ordered_multi') {
    multiSlots =
      question?.accepted_answers.map((answers) => ({ answersText: joinAnswerEditorText(answers) })) ?? [
        { answersText: '' },
        { answersText: '' }
      ];
  } else {
    inlineBlanks =
      question?.accepted_answers.map((answers, index) => ({
        segmentBefore: question.segments[index] ?? '',
        answersText: joinAnswerEditorText(answers)
      })) ?? [{ segmentBefore: '', answersText: '' }];
    inlineTail = question?.segments?.[question.segments.length - 1] ?? '';
  }

  return {
    moduleId,
    prompt,
    questionType,
    rank,
    resetStats,
    singleAnswersText,
    multiSlots,
    inlineBlanks,
    inlineTail,
    bundleTemplate,
    bundleVariants,
    bundleQml,
    qmlText:
      questionType === 'bundle'
        ? ''
        : buildQmlLine(
            buildStructuredDraft({
              prompt,
              questionType,
              singleAnswersText,
              multiSlots,
              inlineBlanks,
              inlineTail,
              bundleQml
            })
          )
  };
}

export function buildQuestionPayload(
  state: EditorState,
  {
    selectedModuleIsLeaf
  }: {
    selectedModuleIsLeaf: boolean;
  }
): QuestionDraftPayload {
  const normalizedModuleId = Number(state.moduleId);
  if (!normalizedModuleId) {
    throw new Error('Select a module before saving.');
  }
  if (!selectedModuleIsLeaf) {
    throw new Error('Questions can only be created in leaf modules.');
  }

  const draft = buildStructuredDraft(state);
  if (state.questionType === 'bundle') {
    if (!state.bundleQml.trim()) {
      throw new Error('Bundle QML is required.');
    }
    return {
      module_id: normalizedModuleId,
      prompt: '',
      question_type: 'bundle',
      rank: state.rank,
      accepted_answers: [],
      segments: [],
      bundle_qml: wrapBundleQml(state.bundleQml.trim())
    };
  }
  if (!draft.prompt) {
    throw new Error('Prompt is required.');
  }
  if (draft.accepted_answers.some((answers) => answers.length === 0)) {
    throw new Error('Every answer slot needs at least one accepted answer.');
  }

  return {
    module_id: normalizedModuleId,
    prompt: draft.prompt,
    question_type: draft.question_type,
    rank: state.rank,
    accepted_answers: draft.accepted_answers,
    segments: draft.segments
  };
}

function createPlaceholder(isEditing: boolean, value: string): string | undefined {
  return isEditing ? undefined : value;
}

export function promptPlaceholder(type: QuestionType, isEditing: boolean): string | undefined {
  switch (type) {
    case 'single_text':
      return createPlaceholder(isEditing, 'What is another name for sodium chloride?');
    case 'multi_text':
      return createPlaceholder(isEditing, 'Name two primary colors.');
    case 'ordered_multi':
      return createPlaceholder(isEditing, 'Name the first two stages in order.');
    case 'bundle':
      return createPlaceholder(isEditing, 'Bundle questions are authored in the bundle QML field below.');
    case 'inline_cloze':
      return createPlaceholder(isEditing, 'The [heart] pumps [blood] through the body.');
  }
}

export function singleAnswerPlaceholder(_type: QuestionType, isEditing: boolean): string | undefined {
  return createPlaceholder(isEditing, 'sodium chloride | table salt');
}

export function multiSlotPlaceholder(type: QuestionType, index: number, isEditing: boolean): string | undefined {
  if (isEditing) {
    return undefined;
  }
  if (type === 'multi_text') {
    return index === 0 ? 'red' : index === 1 ? 'blue' : `answer ${index + 1}`;
  }
  return index === 0 ? 'prophase' : index === 1 ? 'metaphase' : `step ${index + 1}`;
}

export function inlineQmlPlaceholder(isEditing: boolean): string | undefined {
  return createPlaceholder(isEditing, 'The [heart] pumps [blood] through the body.');
}

export function bundleQmlPlaceholder(isEditing: boolean): string | undefined {
  return createPlaceholder(
    isEditing,
    'A patient needs {} mg of active ingredient. The medication has {} mg/ml of active ingredient. How much medication does the patient need? []\n {400} {20} [20]\n {500} {30} [16.7 | 16.67]'
  );
}
