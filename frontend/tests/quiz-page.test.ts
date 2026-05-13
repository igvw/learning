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
    expect(screen.getByText(/suggest changes above/i)).toBeTruthy();
    expect(answeredCard?.className).toContain('incorrect');
    expect(answeredInput.className).toContain('answer-incorrect');
    expect(answerBox?.className).toContain('plain-answer-box');
    const startAnotherQuizButton = screen.getByRole('button', { name: 'Start Another Quiz' });
    await waitFor(() => expect(document.activeElement).toBe(startAnotherQuizButton));
    expect(screen.getByRole('button', { name: 'Suggest change' })).toBeTruthy();
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

  it('shows all accepted answers inside the input for a correct primary single-slot answer', async () => {
    const user = userEvent.setup();
    const openEditSpy = vi.fn().mockResolvedValue(undefined);
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
        onOpenEdit: openEditSpy,
        onSubmit: vi.fn()
      }
    });

    const answeredCard = screen.getByText('1. Which river runs through Cairo?').closest('article');
    const answeredInput = screen.getByRole('textbox');

    expect(answeredCard?.className).toContain('correct');
    expect(answeredInput.className).toContain('answer-correct');
    expect((answeredInput as HTMLInputElement).value).toBe('nile / the nile');
    expect(screen.queryByText('nile')).toBeNull();
    expect(screen.queryByText('nile / the nile')).toBeNull();
    expect(screen.queryByRole('list')).toBeNull();
    await user.click(screen.getByRole('button', { name: 'Suggest change' }));
    expect(openEditSpy).toHaveBeenCalledWith(21);
  });

  it('shows the suggest-change action as soon as a question has been submitted', async () => {
    const user = userEvent.setup();
    const openEditSpy = vi.fn().mockResolvedValue(undefined);
    const session = buildQuizSession({
      id: 29,
      items: [
        buildQuizItem({
          id: 31,
          question_id: 41,
          prompt: 'What is the capital of Norway?',
          submitted_answer: ['Oslo'],
          is_correct: true,
          score_earned: 1,
          score_possible: 1,
          canonical_answers: ['oslo'],
          default_answers: ['oslo'],
          accepted_answer_groups: [['oslo']],
          matched_default_answers: [true]
        }),
        buildQuizItem({
          id: 32,
          position: 2,
          question_id: 42,
          prompt: 'What is the capital of Sweden?'
        })
      ]
    });

    render(QuizPage, {
      props: {
        session,
        moduleLabel: 'Geography',
        busyItemId: null,
        onOpenEdit: openEditSpy,
        onSubmit: vi.fn()
      }
    });

    expect(screen.queryByText('Session complete')).toBeNull();
    expect(screen.getAllByRole('button', { name: 'Suggest change' })).toHaveLength(1);

    await user.click(screen.getByRole('button', { name: 'Suggest change' }));

    expect(openEditSpy).toHaveBeenCalledWith(41);
  });

  it('opens the editor from answered questions only', async () => {
    const user = userEvent.setup();
    const openEditSpy = vi.fn().mockResolvedValue(undefined);
    const session = buildQuizSession({
      id: 34,
      items: [
        buildQuizItem({
          id: 40,
          question_id: 50,
          prompt: 'What is the capital of Germany?',
          submitted_answer: ['Berlin'],
          is_correct: true,
          score_earned: 1,
          score_possible: 1,
          canonical_answers: ['berlin'],
          default_answers: ['berlin'],
          accepted_answer_groups: [['berlin']],
          matched_default_answers: [true]
        }),
        buildQuizItem({
          id: 41,
          position: 2,
          question_id: 51,
          prompt: 'What is the capital of Austria?'
        })
      ]
    });

    render(QuizPage, {
      props: {
        session,
        moduleLabel: 'Geography',
        busyItemId: null,
        onOpenEdit: openEditSpy,
        onSubmit: vi.fn()
      }
    });

    expect(screen.getAllByRole('button', { name: 'Suggest change' })).toHaveLength(1);
    await user.click(screen.getByRole('button', { name: 'Suggest change' }));

    expect(openEditSpy).toHaveBeenCalledWith(50);
  });

  it('does not show suggest-change actions for unanswered questions', () => {
    const session = buildQuizSession({
      id: 30,
      items: [
        buildQuizItem({
          id: 33,
          question_id: 43,
          prompt: 'What is the capital of Denmark?',
          submitted_answer: null,
          is_correct: null
        }),
        buildQuizItem({
          id: 34,
          position: 2,
          question_id: 44,
          prompt: 'What is the capital of Finland?'
        })
      ]
    });

    render(QuizPage, {
      props: {
        session,
        moduleLabel: 'Geography',
        busyItemId: null,
        onOpenEdit: vi.fn(),
        onSubmit: vi.fn()
      }
    });

    expect(screen.queryByRole('button', { name: 'Suggest change' })).toBeNull();
  });

  it('uses Alt+R to open the most recently submitted question for editing', () => {
    const openEditSpy = vi.fn().mockResolvedValue(undefined);
    const session = buildQuizSession({
      id: 31,
      items: [
        buildQuizItem({
          id: 35,
          question_id: 45,
          prompt: 'What is the capital of Iceland?',
          submitted_answer: ['Reykjavik'],
          is_correct: true,
          score_earned: 1,
          score_possible: 1,
          canonical_answers: ['reykjavik'],
          default_answers: ['reykjavik'],
          accepted_answer_groups: [['reykjavik']],
          matched_default_answers: [true]
        }),
        buildQuizItem({
          id: 36,
          position: 2,
          question_id: 46,
          prompt: 'What is the capital of Estonia?'
        })
      ]
    });

    render(QuizPage, {
      props: {
        session,
        moduleLabel: 'Geography',
        busyItemId: null,
        onOpenEdit: openEditSpy,
        onSubmit: vi.fn()
      }
    });

    const event = new KeyboardEvent('keydown', {
      altKey: true,
      bubbles: true,
      cancelable: true,
      code: 'KeyR',
      key: 'r'
    });
    window.dispatchEvent(event);

    expect(event.defaultPrevented).toBe(true);
    expect(openEditSpy).toHaveBeenCalledWith(45);
  });

  it('does not intercept Alt+R when there is no submitted previous question', () => {
    const openEditSpy = vi.fn().mockResolvedValue(undefined);
    const session = buildQuizSession({
      id: 32,
      items: [
        buildQuizItem({
          id: 37,
          question_id: 47,
          prompt: 'What is the capital of Latvia?'
        })
      ]
    });

    render(QuizPage, {
      props: {
        session,
        moduleLabel: 'Geography',
        busyItemId: null,
        onOpenEdit: openEditSpy,
        onSubmit: vi.fn()
      }
    });

    const event = new KeyboardEvent('keydown', {
      altKey: true,
      bubbles: true,
      cancelable: true,
      code: 'KeyR',
      key: 'r'
    });
    window.dispatchEvent(event);

    expect(event.defaultPrevented).toBe(false);
    expect(openEditSpy).not.toHaveBeenCalled();
  });

  it('uses Alt+R on the final submitted item even when completed mistake mode hides it', async () => {
    const user = userEvent.setup();
    const openEditSpy = vi.fn().mockResolvedValue(undefined);
    const session = buildQuizSession({
      id: 33,
      completed_at: '2026-04-04T10:00:00Z',
      items: [
        buildQuizItem({
          id: 38,
          question_id: 48,
          prompt: 'What is the capital of Kenya?',
          submitted_answer: ['Mombasa'],
          is_correct: false,
          score_earned: 0,
          score_possible: 1,
          canonical_answers: ['nairobi'],
          default_answers: ['nairobi'],
          accepted_answer_groups: [['nairobi']],
          matched_default_answers: [false]
        }),
        buildQuizItem({
          id: 39,
          position: 2,
          question_id: 49,
          prompt: 'What is the capital of Japan?',
          submitted_answer: ['Tokyo'],
          is_correct: true,
          score_earned: 1,
          score_possible: 1,
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
        onOpenEdit: openEditSpy,
        onSubmit: vi.fn()
      }
    });

    await user.click(screen.getByRole('button', { name: 'Review Mistakes' }));
    expect(screen.queryByText('2. What is the capital of Japan?')).toBeNull();

    const event = new KeyboardEvent('keydown', {
      altKey: true,
      bubbles: true,
      cancelable: true,
      code: 'KeyR',
      key: 'r'
    });
    window.dispatchEvent(event);

    expect(event.defaultPrevented).toBe(true);
    expect(openEditSpy).toHaveBeenCalledWith(49);
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

  it('shows alternatives in correct slots and only incorrect-slot answers below for incorrect multi-slot submissions', () => {
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
    expect((inputs[0] as HTMLInputElement).value).toBe('head / skull');
    expect((inputs[1] as HTMLInputElement).value).toBe('thorax');
    expect((inputs[2] as HTMLInputElement).value).toBe('legs');
    const answerBox = screen.getByText('abdomen').closest('.answer-box');
    expect(answerBox?.className).toContain('plain-answer-box');
    expect(screen.queryByText('thorax')).toBeNull();
    expect(screen.queryAllByRole('listitem')).toHaveLength(0);
    expect(screen.getByRole('button', { name: 'Suggest change' })).toBeTruthy();
  });

  it('shows all accepted answers in every correct slot for fully correct multi-slot submissions', () => {
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
          submitted_answer: ['head', 'thorax', 'abdomen'],
          is_correct: true,
          score_earned: 1,
          score_possible: 1,
          slot_results: [
            { index: 0, is_correct: true, expected: 'head / skull' },
            { index: 1, is_correct: true, expected: 'thorax' },
            { index: 2, is_correct: true, expected: 'abdomen / belly' }
          ],
          canonical_answers: ['head / skull', 'thorax', 'abdomen / belly'],
          default_answers: ['head', 'thorax', 'abdomen'],
          accepted_answer_groups: [['head', 'skull'], ['thorax'], ['abdomen', 'belly']],
          matched_default_answers: [true, true, true]
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
    expect((inputs[2] as HTMLInputElement).value).toBe('abdomen / belly');
    expect(screen.queryByRole('list')).toBeNull();
  });
});
