import type {
  CreateModulePayload,
  ModuleNode,
  QuestionDraftPayload,
  QuizSession,
  StatsResponse,
  SubmitAnswerResult
} from './types';

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    headers: {
      'Content-Type': 'application/json'
    },
    ...init
  });

  if (!response.ok) {
    let message = `Request failed with ${response.status}`;
    try {
      const payload = await response.json();
      if (payload?.detail) {
        message = payload.detail;
      }
    } catch (error) {
      console.error(error);
    }
    throw new Error(message);
  }

  return (await response.json()) as T;
}

export function getModulesTree(): Promise<ModuleNode[]> {
  return request<ModuleNode[]>('/api/modules/tree');
}

export function createModule(payload: CreateModulePayload): Promise<ModuleNode> {
  return request<ModuleNode>('/api/modules', {
    method: 'POST',
    body: JSON.stringify(payload)
  });
}

export function createQuizSession(moduleId: number | null, count = 10): Promise<QuizSession> {
  return request<QuizSession>('/api/quiz-sessions', {
    method: 'POST',
    body: JSON.stringify({
      module_id: moduleId,
      count
    })
  });
}

export function submitQuizAnswer(
  sessionId: number,
  itemId: number,
  answers: string[]
): Promise<SubmitAnswerResult> {
  return request<SubmitAnswerResult>(`/api/quiz-sessions/${sessionId}/items/${itemId}/submit`, {
    method: 'POST',
    body: JSON.stringify({ answers })
  });
}

export function getStats(moduleId: number | null, reviewOnly: boolean): Promise<StatsResponse> {
  const params = new URLSearchParams();
  if (moduleId !== null) {
    params.set('module_id', String(moduleId));
  }
  params.set('review_only', String(reviewOnly));
  return request<StatsResponse>(`/api/stats?${params.toString()}`);
}

export function createQuestion(payload: QuestionDraftPayload): Promise<{ question_id: number }> {
  return request<{ question_id: number }>('/api/questions', {
    method: 'POST',
    body: JSON.stringify(payload)
  });
}

export function reviseQuestion(
  questionId: number,
  payload: QuestionDraftPayload & { reset_stats: boolean }
): Promise<{ question_id: number }> {
  return request<{ question_id: number }>(`/api/questions/${questionId}/revisions`, {
    method: 'POST',
    body: JSON.stringify(payload)
  });
}

export function setQuestionReviewFlag(
  questionId: number,
  reviewFlag: boolean
): Promise<{ question_id: number; review_flag: boolean }> {
  return request<{ question_id: number; review_flag: boolean }>(`/api/questions/${questionId}/review-flag`, {
    method: 'PATCH',
    body: JSON.stringify({ review_flag: reviewFlag })
  });
}
