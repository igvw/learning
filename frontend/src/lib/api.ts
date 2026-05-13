import type {
  AuthActor,
  BootstrapAdminPayload,
  CreateModulePayload,
  CreateUserPayload,
  HealthResponse,
  LoginPayload,
  ModerationActionPayload,
  ModerationRevisionActionPayload,
  ModerationQueue,
  ModuleNode,
  MyContributions,
  QuestionDraftPayload,
  QuestionImportResult,
  QuestionImportRowPayload,
  QuestionMutationResult,
  QuestionRow,
  QuizSession,
  StatsResponse,
  SubmitAnswerResult,
  UpdateModulePayload,
  UpdateUserPasswordPayload,
  UpdateUserRolePayload,
  User
} from './types';

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const headers = new Headers(init?.headers ?? {});
  if (!headers.has('Content-Type') && init?.body !== undefined) {
    headers.set('Content-Type', 'application/json');
  }

  const response = await fetch(path, {
    credentials: 'same-origin',
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

  if (response.status === 204) {
    return undefined as T;
  }
  return (await response.json()) as T;
}

function requestErrorMessage(response: Response, fallback: string): Promise<string> {
  return response
    .json()
    .then((payload) => (payload?.detail ? String(payload.detail) : fallback))
    .catch((error) => {
      console.error(error);
      return fallback;
    });
}

function filenameFromContentDisposition(value: string | null, fallback: string): string {
  if (!value) {
    return fallback;
  }
  const utf8Match = value.match(/filename\*=UTF-8''([^;]+)/i);
  if (utf8Match) {
    try {
      return decodeURIComponent(utf8Match[1]);
    } catch (error) {
      console.error(error);
    }
  }
  const quotedMatch = value.match(/filename="([^"]+)"/i);
  if (quotedMatch) {
    return quotedMatch[1];
  }
  const plainMatch = value.match(/filename=([^;]+)/i);
  return plainMatch ? plainMatch[1].trim() : fallback;
}

export function getHealth(): Promise<HealthResponse> {
  return request<HealthResponse>('/api/health');
}

export function bootstrapAdmin(payload: BootstrapAdminPayload): Promise<AuthActor> {
  return request<AuthActor>('/api/auth/bootstrap-admin', {
    method: 'POST',
    body: JSON.stringify(payload)
  });
}

export function login(payload: LoginPayload): Promise<AuthActor> {
  return request<AuthActor>('/api/auth/login', {
    method: 'POST',
    body: JSON.stringify(payload)
  });
}

export function logout(): Promise<void> {
  return request<void>('/api/auth/logout', { method: 'POST' });
}

export function getCurrentActor(): Promise<AuthActor> {
  return request<AuthActor>('/api/auth/me');
}

export function getModulesTree(): Promise<ModuleNode[]> {
  return request<ModuleNode[]>('/api/modules/tree');
}

export function getUsers(): Promise<User[]> {
  return request<User[]>('/api/users');
}

export function createUser(payload: CreateUserPayload): Promise<User> {
  return request<User>('/api/users', {
    method: 'POST',
    body: JSON.stringify(payload)
  });
}

export function updateUserPassword(userId: number, payload: UpdateUserPasswordPayload): Promise<{ user_id: number }> {
  return request<{ user_id: number }>(`/api/users/${userId}/password`, {
    method: 'POST',
    body: JSON.stringify(payload)
  });
}

export function updateUserRole(userId: number, payload: UpdateUserRolePayload): Promise<User> {
  return request<User>(`/api/users/${userId}`, {
    method: 'PATCH',
    body: JSON.stringify(payload)
  });
}

export function getMyContributions(): Promise<MyContributions> {
  return request<MyContributions>('/api/contributions/me');
}

export function getModerationQueue(): Promise<ModerationQueue> {
  return request<ModerationQueue>('/api/moderation/queue');
}

export function reviewModule(moduleId: number, payload: ModerationActionPayload): Promise<Record<string, unknown>> {
  return request<Record<string, unknown>>(`/api/moderation/modules/${moduleId}`, {
    method: 'POST',
    body: JSON.stringify(payload)
  });
}

export function deleteRejectedModule(moduleId: number): Promise<void> {
  return request<void>(`/api/moderation/modules/${moduleId}`, {
    method: 'DELETE'
  });
}

export function reviewQuestion(questionId: number, payload: ModerationActionPayload): Promise<Record<string, unknown>> {
  return request<Record<string, unknown>>(`/api/moderation/questions/${questionId}`, {
    method: 'POST',
    body: JSON.stringify(payload)
  });
}

export function reviewQuestionRevision(
  proposalId: number,
  payload: ModerationRevisionActionPayload
): Promise<Record<string, unknown>> {
  return request<Record<string, unknown>>(`/api/moderation/question-revisions/${proposalId}`, {
    method: 'POST',
    body: JSON.stringify(payload)
  });
}

export function createModule(payload: CreateModulePayload): Promise<ModuleNode> {
  return request<ModuleNode>('/api/modules', {
    method: 'POST',
    body: JSON.stringify(payload)
  });
}

export function updateModule(moduleId: number, payload: UpdateModulePayload): Promise<ModuleNode> {
  return request<ModuleNode>(`/api/modules/${moduleId}`, {
    method: 'PATCH',
    body: JSON.stringify(payload)
  });
}

export function deleteModule(moduleId: number): Promise<void> {
  return request<void>(`/api/modules/${moduleId}`, {
    method: 'DELETE'
  });
}

export async function exportContentArchive(): Promise<void> {
  const response = await fetch('/api/modules/export', {
    credentials: 'same-origin'
  });

  if (!response.ok) {
    throw new Error(await requestErrorMessage(response, `Request failed with ${response.status}`));
  }

  const blob = await response.blob();
  const filename = filenameFromContentDisposition(response.headers.get('Content-Disposition'), 'modules-export.zip');
  const objectUrl = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = objectUrl;
  link.download = filename;
  link.style.display = 'none';
  document.body.append(link);

  try {
    link.click();
  } finally {
    link.remove();
    URL.revokeObjectURL(objectUrl);
  }
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

export function submitQuizAnswer(sessionId: number, itemId: number, answers: string[]): Promise<SubmitAnswerResult> {
  return request<SubmitAnswerResult>(`/api/quiz-sessions/${sessionId}/items/${itemId}/submit`, {
    method: 'POST',
    body: JSON.stringify({ answers })
  });
}

export function getQuestion(questionId: number): Promise<QuestionRow> {
  return request<QuestionRow>(`/api/questions/${questionId}`);
}

export function getStats(moduleId: number | null): Promise<StatsResponse> {
  const params = new URLSearchParams();
  if (moduleId !== null) {
    params.set('module_id', String(moduleId));
  }
  const query = params.toString();
  return request<StatsResponse>(query ? `/api/stats?${query}` : '/api/stats');
}

export function createQuestion(payload: QuestionDraftPayload): Promise<QuestionMutationResult> {
  return request<QuestionMutationResult>('/api/questions', {
    method: 'POST',
    body: JSON.stringify(payload)
  });
}

export function reviseQuestion(
  questionId: number,
  payload: QuestionDraftPayload & { reset_stats: boolean }
): Promise<QuestionMutationResult> {
  return request<QuestionMutationResult>(`/api/questions/${questionId}/revisions`, {
    method: 'POST',
    body: JSON.stringify(payload)
  });
}

export function deleteQuestion(questionId: number): Promise<QuestionMutationResult> {
  return request<QuestionMutationResult>(`/api/questions/${questionId}`, {
    method: 'DELETE'
  });
}

export function withdrawQuestionRevision(questionId: number): Promise<void> {
  return request<void>(`/api/questions/${questionId}/revisions/mine`, {
    method: 'DELETE'
  });
}

export function validateQuestionImportText(moduleId: number, qmlText: string): Promise<QuestionImportResult> {
  return request<QuestionImportResult>('/api/question-imports/validate', {
    method: 'POST',
    body: JSON.stringify({ module_id: moduleId, qml_text: qmlText })
  });
}

export function validateQuestionImportRows(
  moduleId: number,
  rows: QuestionImportRowPayload[]
): Promise<QuestionImportResult> {
  return request<QuestionImportResult>('/api/question-imports/validate', {
    method: 'POST',
    body: JSON.stringify({ module_id: moduleId, rows })
  });
}

export function commitQuestionImport(moduleId: number, rows: QuestionImportRowPayload[]): Promise<QuestionImportResult> {
  return request<QuestionImportResult>('/api/question-imports/commit', {
    method: 'POST',
    body: JSON.stringify({ module_id: moduleId, rows })
  });
}
