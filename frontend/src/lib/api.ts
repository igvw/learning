import type {
  CreateModulePayload,
  ModuleNode,
  QuestionDraftPayload,
  QuestionImportRowPayload,
  QuestionImportSession,
  QuizSession,
  StatsResponse,
  SubmitAnswerResult,
  User
} from './types';

async function request<T>(path: string, init?: RequestInit, userId?: number | null): Promise<T> {
  const headers = new Headers(init?.headers ?? {});
  if (!headers.has('Content-Type') && init?.body !== undefined) {
    headers.set('Content-Type', 'application/json');
  }
  if (userId !== null && userId !== undefined) {
    headers.set('X-User-Id', String(userId));
  }

  const response = await fetch(path, {
    headers,
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

export function getUsers(): Promise<User[]> {
  return request<User[]>('/api/users');
}

export function createUser(payload: { handle: string; display_name: string }): Promise<User> {
  return request<User>(
    '/api/users',
    {
      method: 'POST',
      body: JSON.stringify(payload)
    }
  );
}

export function createModule(payload: CreateModulePayload): Promise<ModuleNode> {
  return request<ModuleNode>('/api/modules', {
    method: 'POST',
    body: JSON.stringify(payload)
  });
}

export function createQuizSession(userId: number, moduleId: number | null, count = 10): Promise<QuizSession> {
  return request<QuizSession>(
    '/api/quiz-sessions',
    {
      method: 'POST',
      body: JSON.stringify({
        module_id: moduleId,
        count
      })
    },
    userId
  );
}

export function submitQuizAnswer(
  userId: number,
  sessionId: number,
  itemId: number,
  answers: string[]
): Promise<SubmitAnswerResult> {
  return request<SubmitAnswerResult>(
    `/api/quiz-sessions/${sessionId}/items/${itemId}/submit`,
    {
      method: 'POST',
      body: JSON.stringify({ answers })
    },
    userId
  );
}

export function getStats(userId: number, moduleId: number | null, reviewOnly: boolean): Promise<StatsResponse> {
  const params = new URLSearchParams();
  if (moduleId !== null) {
    params.set('module_id', String(moduleId));
  }
  params.set('review_only', String(reviewOnly));
  return request<StatsResponse>(`/api/stats?${params.toString()}`, undefined, userId);
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
  userId: number,
  questionId: number,
  reviewFlag: boolean
): Promise<{ question_id: number; review_flag: boolean }> {
  return request<{ question_id: number; review_flag: boolean }>(
    `/api/questions/${questionId}/review-flag`,
    {
      method: 'PATCH',
      body: JSON.stringify({ review_flag: reviewFlag })
    },
    userId
  );
}

export function createQuestionImportSession(moduleId: number, csvText: string): Promise<QuestionImportSession> {
  return request<QuestionImportSession>('/api/question-import-sessions', {
    method: 'POST',
    body: JSON.stringify({ module_id: moduleId, csv_text: csvText })
  });
}

export function revalidateQuestionImportSession(
  sessionId: number,
  rows: QuestionImportRowPayload[]
): Promise<QuestionImportSession> {
  return request<QuestionImportSession>(`/api/question-import-sessions/${sessionId}/revalidate`, {
    method: 'POST',
    body: JSON.stringify({ rows })
  });
}

export function discardQuestionImportSessionRow(
  sessionId: number,
  rowNumber: number
): Promise<QuestionImportSession> {
  return request<QuestionImportSession>(`/api/question-import-sessions/${sessionId}/rows/${rowNumber}`, {
    method: 'DELETE'
  });
}

export function commitQuestionImportSession(sessionId: number): Promise<QuestionImportSession> {
  return request<QuestionImportSession>(`/api/question-import-sessions/${sessionId}/commit`, {
    method: 'POST'
  });
}
