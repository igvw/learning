import { render, screen, waitFor } from '@testing-library/svelte';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import QuizPage from '../src/components/QuizPage.svelte';
import { buildQuizItem, buildQuizSession } from './builders';

describe('QuizPage', () => {
  it('submits a single-answer prompt with Enter', async () => {
    const user = userEvent.setup();
    const submitSpy = vi.fn().mockResolvedValue(undefined);
    const session = buildQuizSession({
      id: 22,
      items: [
        buildQuizItem({
          id: 7,
          question_id: 10,
          module_id: 5,
          prompt: 'What is the capital of Japan?',
          rank: 5
        })
      ]
    });

    render(QuizPage, {
      props: {
        session,
        moduleLabel: 'All Modules',
        busyItemId: null,
        onSubmit: submitSpy
      }
    });

    await user.type(screen.getByRole('textbox'), 'Tokyo{enter}');

    expect(submitSpy).toHaveBeenCalledWith(7, ['Tokyo']);
  });

  it('moves through multi-answer inputs with Enter and submits from the last one', async () => {
    const user = userEvent.setup();
    const submitSpy = vi.fn().mockResolvedValue(undefined);
    const session = buildQuizSession({
      id: 24,
      items: [
        buildQuizItem({
          id: 9,
          question_id: 12,
          module_id: 5,
          prompt: 'Name the capitals of Spain and Portugal.',
          question_type: 'ordered_multi',
          rank: 3,
          type_config: { expected_slots: 2 }
        })
      ]
    });

    const view = render(QuizPage, {
      props: {
        session,
        moduleLabel: 'Geography',
        busyItemId: null,
        onSubmit: submitSpy
      }
    });

    const inputs = view.getAllByRole('textbox');
    await user.type(inputs[0], 'Madrid{enter}');
    expect(document.activeElement).toBe(inputs[1]);

    await user.type(inputs[1], 'Lisbon{enter}');
    expect(submitSpy).toHaveBeenCalledWith(9, ['Madrid', 'Lisbon']);
  });

  it('shows all accepted answers in the feedback box for an incorrect submission and focuses the completion action', async () => {
    const session = buildQuizSession({
      id: 23,
      completed_at: '2026-04-04T10:00:00Z',
      items: [
        buildQuizItem({
          id: 8,
          question_id: 11,
          module_id: 5,
          prompt: 'What is the capital of Kenya?',
          submitted_answer: ['Mombasa'],
          is_correct: false,
          score_earned: 0,
          score_possible: 1,
          slot_results: [{ index: 0, is_correct: false, expected: 'nairobi' }],
          canonical_answers: ['nairobi / nairobi city'],
          default_answers: ['nairobi'],
          accepted_answer_groups: [['nairobi', 'nairobi city']],
          matched_default_answers: [false]
        })
      ]
    });

    render(QuizPage, {
      props: {
        session,
        moduleLabel: 'Geography',
        busyItemId: null,
        onSubmit: vi.fn()
      }
    });

    const answeredCard = screen.getByText('1. What is the capital of Kenya?').closest('article');
    const answeredInput = screen.getByRole('textbox');
    const answerBox = screen.getByText('nairobi / nairobi city').closest('.answer-box');

    expect(screen.queryByText('Needs review')).toBeNull();
    expect(screen.queryByText('Accepted answers')).toBeNull();
    expect(screen.queryByText(/Slot 1:/)).toBeNull();
    expect(screen.queryAllByRole('listitem')).toHaveLength(0);
    expect(screen.getByText(/questions above for revision/i)).toBeTruthy();
    expect(answeredCard?.className).toContain('incorrect');
    expect(answeredInput.className).toContain('answer-incorrect');
    expect(answerBox?.className).toContain('plain-answer-box');
    const startAnotherQuizButton = screen.getByRole('button', { name: 'Start Another Quiz' });
    await waitFor(() => expect(document.activeElement).toBe(startAnotherQuizButton));
    expect(screen.getByRole('button', { name: 'Flag for revision' })).toBeTruthy();
  });

  it('lets you choose the number of questions before starting a quiz', async () => {
    const user = userEvent.setup();
    const changeSpy = vi.fn();

    render(QuizPage, {
      props: {
        session: null,
        moduleLabel: 'Geography',
        questionCount: 10,
        onChangeQuestionCount: changeSpy,
        onStartQuiz: vi.fn(),
        onSubmit: vi.fn()
      }
    });

    const input = screen.getByRole('spinbutton', { name: 'Questions per quiz' });
    await user.clear(input);
    await user.type(input, '15');
    await user.tab();

    expect(changeSpy).toHaveBeenCalledWith(15);
  });

  it('filters the completed session down to mistakes only', async () => {
    const user = userEvent.setup();
    const session = buildQuizSession({
      id: 24,
      completed_at: '2026-04-04T10:00:00Z',
      items: [
        buildQuizItem({
          id: 8,
          question_id: 11,
          module_id: 5,
          prompt: 'What is the capital of Kenya?',
          submitted_answer: ['Mombasa'],
          is_correct: false,
          score_earned: 0,
          score_possible: 1,
          slot_results: [{ index: 0, is_correct: false, expected: 'nairobi' }],
          canonical_answers: ['nairobi'],
          default_answers: ['nairobi'],
          accepted_answer_groups: [['nairobi']],
          matched_default_answers: [false]
        }),
        buildQuizItem({
          id: 9,
          position: 2,
          question_id: 12,
          module_id: 5,
          prompt: 'What is the capital of Japan?',
          rank: 2,
          submitted_answer: ['Tokyo'],
          is_correct: true,
          score_earned: 1,
          score_possible: 1,
          slot_results: [{ index: 0, is_correct: true, expected: 'tokyo' }],
          canonical_answers: ['tokyo'],
          default_answers: ['tokyo'],
          accepted_answer_groups: [['tokyo']],
          matched_default_answers: [true]
        })
      ]
    });

    render(QuizPage, {
      props: {
        session,
        moduleLabel: 'Geography',
        busyItemId: null,
        onSubmit: vi.fn()
      }
    });

    expect(screen.getByText('1. What is the capital of Kenya?')).toBeTruthy();
    expect(screen.getByText('2. What is the capital of Japan?')).toBeTruthy();

    await user.click(screen.getByRole('button', { name: 'Review Mistakes' }));

    expect(screen.getByText('1. What is the capital of Kenya?')).toBeTruthy();
    expect(screen.queryByText('2. What is the capital of Japan?')).toBeNull();
    expect(screen.getByRole('button', { name: 'Show All Answers' })).toBeTruthy();
  });

  it('marks a completed question for revision', async () => {
    const user = userEvent.setup();
    const markSpy = vi.fn().mockResolvedValue(undefined);
    const session = buildQuizSession({
      id: 25,
      completed_at: '2026-04-04T10:00:00Z',
      items: [
        buildQuizItem({
          id: 18,
          question_id: 21,
          module_id: 3,
          prompt: 'Which river runs through Cairo?',
          rank: 5,
          submitted_answer: ['Nile'],
          is_correct: true,
          score_earned: 1,
          score_possible: 1,
          canonical_answers: ['nile / the nile'],
          default_answers: ['nile'],
          accepted_answer_groups: [['nile', 'the nile']],
          matched_default_answers: [true]
        })
      ]
    });

    render(QuizPage, {
      props: {
        session,
        moduleLabel: 'Geography',
        busyItemId: null,
        markingReviewQuestionId: null,
        onMarkForRevision: markSpy,
        onSubmit: vi.fn()
      }
    });

    const answeredCard = screen.getByText('1. Which river runs through Cairo?').closest('article');
    const answeredInput = screen.getByRole('textbox');

    expect(answeredCard?.className).toContain('correct');
    expect(answeredInput.className).toContain('answer-correct');
    expect((answeredInput as HTMLInputElement).value).toBe('Nile');
    expect(screen.queryByText('nile')).toBeNull();
    expect(screen.queryByText('nile / the nile')).toBeNull();
    expect(screen.queryByRole('list')).toBeNull();
    await user.click(screen.getByRole('button', { name: 'Flag for revision' }));
    expect(markSpy).toHaveBeenCalledWith(21);
  });

  it('shows all accepted answers inside the input when a correct alternative is submitted', () => {
    const session = buildQuizSession({
      id: 27,
      completed_at: '2026-04-04T10:00:00Z',
      items: [
        buildQuizItem({
          id: 20,
          question_id: 23,
          module_id: 3,
          prompt: 'Which river runs through Cairo?',
          rank: 5,
          submitted_answer: ['the nile'],
          is_correct: true,
          score_earned: 1,
          score_possible: 1,
          slot_results: [{ index: 0, is_correct: true, expected: 'nile / the nile' }],
          canonical_answers: ['nile / the nile'],
          default_answers: ['nile'],
          accepted_answer_groups: [['nile', 'the nile']],
          matched_default_answers: [false]
        })
      ]
    });

    render(QuizPage, {
      props: {
        session,
        moduleLabel: 'Geography',
        busyItemId: null,
        onSubmit: vi.fn()
      }
    });

    const answeredInput = screen.getByRole('textbox');
    expect((answeredInput as HTMLInputElement).value).toBe('nile / the nile');
    expect(screen.queryByRole('list')).toBeNull();
    expect(screen.queryByText('nile / the nile')).toBeNull();
  });

  it('keeps submitted input values and shows full accepted answers below for incorrect multi-slot submissions', () => {
    const session = buildQuizSession({
      id: 26,
      completed_at: '2026-04-04T10:00:00Z',
      items: [
        buildQuizItem({
          id: 19,
          question_id: 22,
          module_id: 2,
          prompt: 'Name the three major body sections of an insect.',
          question_type: 'ordered_multi',
          rank: 4,
          type_config: { expected_slots: 3 },
          submitted_answer: ['head', 'thorax', 'legs'],
          is_correct: false,
          score_earned: 2 / 3,
          score_possible: 1,
          slot_results: [
            { index: 0, is_correct: true, expected: 'head' },
            { index: 1, is_correct: true, expected: 'thorax' },
            { index: 2, is_correct: false, expected: 'abdomen' }
          ],
          canonical_answers: ['head / skull', 'thorax', 'abdomen'],
          default_answers: ['head', 'thorax', 'abdomen'],
          accepted_answer_groups: [['head', 'skull'], ['thorax'], ['abdomen']],
          matched_default_answers: [false, true, false]
        })
      ]
    });

    const view = render(QuizPage, {
      props: {
        session,
        moduleLabel: 'Biology',
        busyItemId: null,
        onSubmit: vi.fn()
      }
    });

    const inputs = view.getAllByRole('textbox');
    expect(screen.getByText('2/3')).toBeTruthy();
    expect(inputs[0].className).toContain('answer-correct');
    expect(inputs[1].className).toContain('answer-correct');
    expect(inputs[2].className).toContain('answer-incorrect');
    expect((inputs[0] as HTMLInputElement).value).toBe('head');
    expect((inputs[1] as HTMLInputElement).value).toBe('thorax');
    expect((inputs[2] as HTMLInputElement).value).toBe('legs');
    expect(screen.getByText('head / skull')).toBeTruthy();
    expect(screen.getByText('thorax')).toBeTruthy();
    expect(screen.getByText('abdomen')).toBeTruthy();
    expect(screen.getAllByRole('listitem')).toHaveLength(3);
    expect(screen.getByRole('button', { name: 'Flag for revision' })).toBeTruthy();
  });

  it('only expands the slots that used non-primary correct answers for fully correct multi-slot submissions', () => {
    const session = buildQuizSession({
      id: 28,
      completed_at: '2026-04-04T10:00:00Z',
      items: [
        buildQuizItem({
          id: 21,
          question_id: 24,
          module_id: 2,
          prompt: 'Name the three major body sections of an insect.',
          question_type: 'ordered_multi',
          rank: 4,
          type_config: { expected_slots: 3 },
          submitted_answer: ['skull', 'thorax', 'abdomen'],
          is_correct: true,
          score_earned: 1,
          score_possible: 1,
          slot_results: [
            { index: 0, is_correct: true, expected: 'head / skull' },
            { index: 1, is_correct: true, expected: 'thorax' },
            { index: 2, is_correct: true, expected: 'abdomen' }
          ],
          canonical_answers: ['head / skull', 'thorax', 'abdomen'],
          default_answers: ['head', 'thorax', 'abdomen'],
          accepted_answer_groups: [['head', 'skull'], ['thorax'], ['abdomen']],
          matched_default_answers: [false, true, true]
        })
      ]
    });

    const view = render(QuizPage, {
      props: {
        session,
        moduleLabel: 'Biology',
        busyItemId: null,
        onSubmit: vi.fn()
      }
    });

    const inputs = view.getAllByRole('textbox');
    expect((inputs[0] as HTMLInputElement).value).toBe('head / skull');
    expect((inputs[1] as HTMLInputElement).value).toBe('thorax');
    expect((inputs[2] as HTMLInputElement).value).toBe('abdomen');
    expect(screen.queryByRole('list')).toBeNull();
  });
});
