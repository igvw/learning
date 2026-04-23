import { buildQmlLine, parseQmlLine } from './qml';
import type {
  ModuleNode,
  QuestionDraftPayload,
  QuestionRow,
  QuestionType
} from './types';

export type FlatModule = { id: number; label: string; isLeaf: boolean };
export type MultiSlot = { answersText: string };
export type InlineBlank = { segmentBefore: string; answersText: string };

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

function splitLines(value: string): string[] {
  return value
    .split('\n')
    .map((entry) => entry.trim())
    .filter(Boolean);
}

export function flattenModules(nodes: ModuleNode[]): FlatModule[] {
  return nodes.flatMap((node) => [
    { id: node.id, label: node.full_slug, isLeaf: node.children.length === 0 },
    ...flattenModules(node.children)
  ]);
}

export function defaultCreateModuleId(modules: ModuleNode[], defaultModuleId: number | null): number {
  const options = flattenModules(modules);
  if (defaultModuleId !== null && options.some((option) => option.id === defaultModuleId)) {
    return defaultModuleId;
  }
  return options[0]?.id ?? 0;
}

export function buildStructuredDraft(
  state: Pick<EditorState, 'prompt' | 'questionType' | 'singleAnswersText' | 'multiSlots' | 'inlineBlanks' | 'inlineTail' | 'bundleQml'>
): StructuredDraft {
  if (state.questionType === 'bundle') {
    return {
      prompt: '',
      question_type: 'bundle',
      accepted_answers: [],
      segments: [],
      bundle_qml: state.bundleQml.trim()
    };
  }
  if (state.questionType === 'single_text') {
    return {
      prompt: state.prompt.trim(),
      question_type: state.questionType,
      accepted_answers: [splitLines(state.singleAnswersText)],
      segments: []
    };
  }
  if (state.questionType === 'multi_text' || state.questionType === 'ordered_multi') {
    return {
      prompt: state.prompt.trim(),
      question_type: state.questionType,
      accepted_answers: state.multiSlots.map((slot) => splitLines(slot.answersText)),
      segments: []
    };
  }
  return {
    prompt: state.prompt.trim(),
    question_type: state.questionType,
    accepted_answers: state.inlineBlanks.map((blank) => splitLines(blank.answersText)),
    segments: [...state.inlineBlanks.map((blank) => blank.segmentBefore), state.inlineTail]
  };
}

export function parseEditorStateFromQml(
  value: string
): Pick<EditorState, 'prompt' | 'questionType' | 'singleAnswersText' | 'multiSlots' | 'inlineBlanks' | 'inlineTail' | 'bundleQml'> {
  const parsed = parseQmlLine(value);
  if (parsed.question_type === 'bundle') {
    return {
      prompt: parsed.prompt,
      questionType: 'bundle',
      singleAnswersText: '',
      multiSlots: [],
      inlineBlanks: [],
      inlineTail: '',
      bundleQml: parsed.bundle_qml ?? value
    };
  }
  if (parsed.question_type === 'single_text') {
    return {
      prompt: parsed.prompt,
      questionType: parsed.question_type,
      singleAnswersText: (parsed.accepted_answers[0] ?? []).join('\n'),
      multiSlots: [],
      inlineBlanks: [],
      inlineTail: '',
      bundleQml: ''
    };
  }
  if (parsed.question_type === 'multi_text' || parsed.question_type === 'ordered_multi') {
    return {
      prompt: parsed.prompt,
      questionType: parsed.question_type,
      singleAnswersText: '',
      multiSlots: parsed.accepted_answers.map((answers) => ({ answersText: answers.join('\n') })),
      inlineBlanks: [],
      inlineTail: '',
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
      answersText: answers.join('\n')
    })),
    inlineTail: parsed.segments[parsed.segments.length - 1] ?? '',
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
  let bundleQml = question?.bundle_qml ?? '';

  if (questionType === 'bundle') {
    bundleQml = question?.bundle_qml ?? '';
  } else if (questionType === 'single_text') {
    singleAnswersText = (question?.accepted_answers?.[0] ?? []).join('\n');
  } else if (questionType === 'multi_text' || questionType === 'ordered_multi') {
    multiSlots =
      question?.accepted_answers.map((answers) => ({ answersText: answers.join('\n') })) ?? [
        { answersText: '' },
        { answersText: '' }
      ];
  } else {
    inlineBlanks =
      question?.accepted_answers.map((answers, index) => ({
        segmentBefore: question.segments[index] ?? '',
        answersText: answers.join('\n')
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
    bundleQml,
    qmlText: buildQmlLine(
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
      bundle_qml: state.bundleQml.trim()
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
      return createPlaceholder(isEditing, 'What is the capital of Norway?');
    case 'multi_text':
      return createPlaceholder(isEditing, 'Name the two rivers that meet at Khartoum.');
    case 'ordered_multi':
      return createPlaceholder(isEditing, 'Name the stages in order.');
    case 'bundle':
      return createPlaceholder(isEditing, 'Bundle questions are authored as canonical bundle QML below.');
    case 'inline_cloze':
      return createPlaceholder(isEditing, 'The [Amazon | Amazon River] flows through South America.');
  }
}

export function singleAnswerPlaceholder(type: QuestionType, isEditing: boolean): string | undefined {
  return createPlaceholder(isEditing, 'oslo');
}

export function multiSlotPlaceholder(type: QuestionType, index: number, isEditing: boolean): string | undefined {
  if (isEditing) {
    return undefined;
  }
  if (type === 'multi_text') {
    return index === 0 ? 'white nile' : index === 1 ? 'blue nile' : `answer ${index + 1}`;
  }
  return index === 0 ? 'stage one' : index === 1 ? 'stage two' : `stage ${index + 1}`;
}

export function inlineSegmentPlaceholder(index: number, isEditing: boolean): string | undefined {
  return isEditing ? undefined : index === 0 ? 'The derivative of ' : ' is ';
}

export function inlineBlankPlaceholder(index: number, isEditing: boolean): string | undefined {
  return isEditing ? undefined : index === 0 ? 'x^2' : '2x';
}

export function inlineTailPlaceholder(isEditing: boolean): string | undefined {
  return isEditing ? undefined : '.';
}
