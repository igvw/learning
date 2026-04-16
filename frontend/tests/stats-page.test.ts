import './test-support';

import { render, screen, waitFor, within } from '@testing-library/svelte';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import StatsPage from '../src/components/StatsPage.svelte';
import { buildQuestionRow, buildRecentSession, buildStatsResponse } from './builders';
import {
  buildFirstSeenGraph,
  buildRecoveryStageGraph,
  buildRetryEligibilityGraph,
  buildRetryEligibilityHourlyGraph,
  buildRetryEligibilityLongRangeGraph
} from '../src/lib/stats-page';

describe('StatsPage', () => {
  it('builds retry eligibility counts across the coming week from fixed buckets only', () => {
    const referenceTime = new Date(2026, 3, 5, 10, 30, 0);
    const localIso = (year: number, monthIndex: number, day: number, hours: number, minutes = 0): string =>
      new Date(year, monthIndex, day, hours, minutes, 0).toISOString();

    const buildRetryQuestion = (questionId: number, prompt: string, schedule: Parameters<typeof buildQuestionRow>[0]['schedule']) =>
      buildQuestionRow({
        question_id: questionId,
        prompt,
        prompt_preview: prompt,
        rank: questionId,
        attempts: questionId === 15 ? 0 : 1,
        correct_percentage: questionId === 15 ? 0 : 1,
        first_asked_at: questionId === 15 ? null : '2026-04-05T09:00:00Z',
        last_asked_at: questionId === 15 ? null : '2026-04-05T09:00:00Z',
        review_flag: questionId === 13,
        schedule
      });

    const graph = buildRetryEligibilityGraph([
      buildRetryQuestion(1, 'one hour later today', {
        bucket: 'cooling',
        logical_bucket: '1h',
        interval_step: 0,
        next_due_at: localIso(2026, 3, 5, 11, 0)
      }),
      buildRetryQuestion(2, 'one day later today', {
        bucket: 'cooling',
        logical_bucket: '1d',
        interval_step: 4,
        next_due_at: localIso(2026, 3, 5, 23, 0)
      }),
      buildRetryQuestion(3, 'one day tomorrow', {
        bucket: 'cooling',
        logical_bucket: '1d',
        interval_step: 4,
        next_due_at: localIso(2026, 3, 6, 9, 0)
      }),
      buildRetryQuestion(4, 'twelve hours tomorrow', {
        bucket: 'cooling',
        logical_bucket: '12h',
        interval_step: 3,
        next_due_at: localIso(2026, 3, 6, 7, 0)
      }),
      buildRetryQuestion(5, 'three day overdue', {
        bucket: 'due_review',
        logical_bucket: '3d',
        interval_step: 5,
        next_due_at: localIso(2026, 3, 4, 10, 0)
      }),
      buildRetryQuestion(6, 'seven day retry pending', {
        bucket: 'due_review',
        logical_bucket: '7d',
        interval_step: 6,
        next_due_at: null,
        retry_pending: true
      }),
      buildRetryQuestion(7, 'three day in two days', {
        bucket: 'cooling',
        logical_bucket: '3d',
        interval_step: 5,
        next_due_at: localIso(2026, 3, 7, 10, 0)
      }),
      buildRetryQuestion(8, 'seven day in four days', {
        bucket: 'cooling',
        logical_bucket: '7d',
        interval_step: 6,
        next_due_at: localIso(2026, 3, 9, 10, 0)
      }),
      buildRetryQuestion(9, 'fourteen day in seven days', {
        bucket: 'cooling',
        logical_bucket: '14d',
        interval_step: 7,
        next_due_at: localIso(2026, 3, 12, 10, 0)
      }),
      buildRetryQuestion(10, 'thirty day future', {
        bucket: 'cooling',
        logical_bucket: '30d',
        interval_step: 8,
        next_due_at: localIso(2026, 3, 20, 10, 0)
      }),
      buildRetryQuestion(11, 'sixty day future', {
        bucket: 'cooling',
        logical_bucket: '60d',
        interval_step: 9,
        next_due_at: localIso(2026, 5, 10, 10, 0)
      }),
      buildRetryQuestion(12, 'missing due date', {
        bucket: 'cooling',
        logical_bucket: '3d',
        interval_step: 5,
        next_due_at: null,
        retry_pending: false
      }),
      buildRetryQuestion(13, 'review', {
        bucket: 'hot0',
        logical_bucket: 'review',
        recovery_streak: 0,
        interval_step: 0,
        next_due_at: null,
        retry_pending: true
      }),
      buildRetryQuestion(14, 'mastery', {
        bucket: 'mastery',
        logical_bucket: 'mastery'
      }),
      buildRetryQuestion(15, 'unseen', {
        bucket: 'unseen',
        logical_bucket: 'unseen'
      })
    ], referenceTime);

    expect(graph.days.map((day) => day.label)).toEqual(['<1', '1', '2', '3', '4', '5', '6', '7', '>7']);
    expect(graph.days.map((day) => day.count)).toEqual([4, 2, 1, 0, 1, 0, 0, 1, 2]);
  });

  it('builds spaced repetition stage counts including 30d and 60d', () => {
    const graph = buildRecoveryStageGraph([
      buildQuestionRow({
        question_id: 1,
        schedule: {
          bucket: 'cooling',
          logical_bucket: '30d',
          interval_step: 8,
          next_due_at: '2026-05-05T10:00:00Z'
        }
      }),
      buildQuestionRow({
        question_id: 2,
        schedule: {
          bucket: 'due_review',
          logical_bucket: '30d',
          interval_step: 8,
          next_due_at: '2026-05-05T10:00:00Z'
        }
      }),
      buildQuestionRow({
        question_id: 3,
        schedule: {
          bucket: 'cooling',
          logical_bucket: '60d',
          interval_step: 9,
          next_due_at: '2026-06-05T10:00:00Z'
        }
      })
    ]);

    expect(graph.stages.map((stage) => stage.label)).toContain('30d');
    expect(graph.stages.map((stage) => stage.label)).toContain('60d');
    expect(graph.stages.find((stage) => stage.key === '30d')?.count).toBe(2);
    expect(graph.stages.find((stage) => stage.key === '30d')?.coolingCount).toBe(1);
    expect(graph.stages.find((stage) => stage.key === '60d')?.count).toBe(1);
  });

  it('builds hourly retry detail from the current <1 group only', () => {
    const referenceTime = new Date(2026, 3, 5, 10, 30, 0);
    const localIso = (year: number, monthIndex: number, day: number, hours: number, minutes = 0): string =>
      new Date(year, monthIndex, day, hours, minutes, 0).toISOString();

    const graph = buildRetryEligibilityHourlyGraph([
      buildQuestionRow({
        question_id: 1,
        schedule: {
          bucket: 'due_review',
          logical_bucket: '7d',
          interval_step: 6,
          retry_pending: true
        }
      }),
      buildQuestionRow({
        question_id: 2,
        schedule: {
          bucket: 'cooling',
          logical_bucket: '1h',
          interval_step: 0,
          next_due_at: localIso(2026, 3, 5, 10, 45)
        }
      }),
      buildQuestionRow({
        question_id: 3,
        schedule: {
          bucket: 'cooling',
          logical_bucket: '3h',
          interval_step: 1,
          next_due_at: localIso(2026, 3, 5, 12, 15)
        }
      }),
      buildQuestionRow({
        question_id: 4,
        schedule: {
          bucket: 'cooling',
          logical_bucket: '1d',
          interval_step: 4,
          next_due_at: localIso(2026, 3, 5, 15, 45)
        }
      }),
      buildQuestionRow({
        question_id: 5,
        schedule: {
          bucket: 'cooling',
          logical_bucket: '12h',
          interval_step: 3,
          next_due_at: localIso(2026, 3, 6, 7, 0)
        }
      }),
      buildQuestionRow({
        question_id: 6,
        review_flag: true,
        schedule: {
          bucket: 'hot0',
          logical_bucket: 'review',
          retry_pending: true
        }
      })
    ], referenceTime);

    expect(graph.hours).toHaveLength(24);
    expect(graph.hours[0]?.count).toBe(2);
    expect(graph.hours[2]?.count).toBe(1);
    expect(graph.hours[5]?.count).toBe(1);
    expect(graph.hours[0]?.label).toBe('10:00');
    expect(graph.hours[4]?.label).toBe('14:00');
    expect(graph.hours[0]?.fullLabel).toContain('10:00');
    expect(graph.hours.reduce((total, hour) => total + hour.count, 0)).toBe(4);
  });

  it('builds weekly retry detail from the current >7 group only', () => {
    const referenceTime = new Date(2026, 3, 5, 10, 30, 0);
    const localIso = (year: number, monthIndex: number, day: number, hours: number, minutes = 0): string =>
      new Date(year, monthIndex, day, hours, minutes, 0).toISOString();

    const graph = buildRetryEligibilityLongRangeGraph([
      buildQuestionRow({
        question_id: 1,
        schedule: {
          bucket: 'cooling',
          logical_bucket: '30d',
          interval_step: 8,
          next_due_at: localIso(2026, 3, 13, 11, 0)
        }
      }),
      buildQuestionRow({
        question_id: 2,
        schedule: {
          bucket: 'cooling',
          logical_bucket: '60d',
          interval_step: 9,
          next_due_at: localIso(2026, 3, 21, 10, 0)
        }
      }),
      buildQuestionRow({
        question_id: 3,
        schedule: {
          bucket: 'cooling',
          logical_bucket: '14d',
          interval_step: 7,
          next_due_at: localIso(2027, 4, 20, 10, 0)
        }
      }),
      buildQuestionRow({
        question_id: 4,
        schedule: {
          bucket: 'cooling',
          logical_bucket: '7d',
          interval_step: 6,
          next_due_at: localIso(2026, 3, 8, 10, 0)
        }
      })
    ], referenceTime);

    expect(graph.weeks).toHaveLength(52);
    expect(graph.weeks[0]?.count).toBe(1);
    expect(graph.weeks[1]?.count).toBe(1);
    expect(graph.weeks.reduce((total, week) => total + week.count, 0)).toBe(2);
  });

  it('builds first-time answered counts across the last 7 local days', () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date('2026-04-10T12:00:00Z'));

    const buildQuestion = (questionId: number, firstAskedAt: string | null) =>
      buildQuestionRow({
        question_id: questionId,
        prompt: `question ${questionId}`,
        prompt_preview: `question ${questionId}`,
        rank: questionId,
        attempts: firstAskedAt ? 1 : 0,
        correct_percentage: 1,
        first_asked_at: firstAskedAt,
        last_asked_at: firstAskedAt,
        schedule: {
          bucket: 'cooling',
          logical_bucket: '1h',
          interval_step: 0
        }
      });

    const graph = buildFirstSeenGraph([
      buildQuestion(1, '2026-04-10T08:00:00Z'),
      buildQuestion(2, '2026-04-10T09:00:00Z'),
      buildQuestion(3, '2026-04-09T08:00:00Z'),
      buildQuestion(4, '2026-04-07T08:00:00Z'),
      buildQuestion(5, '2026-04-04T08:00:00Z'),
      buildQuestion(6, '2026-04-03T08:00:00Z'),
      buildQuestion(7, null),
      buildQuestion(8, '2026-04-02T08:00:00Z')
    ]);

    expect(graph.days).toHaveLength(7);
    expect(graph.days.map((day) => day.count)).toEqual([1, 0, 0, 1, 0, 1, 2]);
  });

  it('filters the single table to review questions, keeps graphs visible, and sorts the displayed rows', async () => {
    const user = userEvent.setup();
    const openSpy = vi.fn();
    const toggleSpy = vi.fn();
    const stats = buildStatsResponse({
      summary: {
        total_questions: 4,
        reviewed_questions: 2,
        total_attempts: 7,
        total_correct: 4,
        total_possible: 6,
        accuracy: 2 / 3
      },
      recent_sessions: [
        buildRecentSession({
          session_id: 11,
          created_at: '2026-04-04T11:00:00Z',
          answered_count: 2,
          correct_count: 2,
          score_possible: 2,
          accuracy: 1
        }),
        buildRecentSession({
          session_id: 10,
          created_at: '2026-04-04T10:00:00Z',
          answered_count: 3,
          correct_count: 2,
          score_possible: 3,
          accuracy: 2 / 3
        })
      ],
      questions: [
        buildQuestionRow({
          question_id: 50,
          module_id: 3,
          module_full_slug: 'biology/plants',
          prompt: 'What structure anchors most plants in the ground?',
          prompt_preview: 'What structure anchors most plants in the ground?',
          rank: 2,
          attempts: 3,
          correct_percentage: 2 / 3,
          first_asked_at: '2026-04-01T06:00:00Z',
          last_asked_at: '2026-04-01T06:00:00Z',
          review_flag: true,
          accepted_answers: [['roots']],
          recent_incorrect_answers: [
            {
              answer_text: 'stems',
              count: 2,
              latest_answered_at: '2026-04-04T08:00:00Z'
            }
          ],
          schedule: {
            bucket: 'hot1_sit_out',
            logical_bucket: 'review',
            recovery_streak: 1,
            interval_step: 0,
            last_incorrect_at: '2026-04-04T08:00:00Z'
          }
        }),
        buildQuestionRow({
          question_id: 51,
          module_id: 5,
          module_full_slug: 'geography/capitals',
          prompt: 'What is the capital of Canada?',
          prompt_preview: 'What is the capital of Canada?',
          rank: 5,
          attempts: 7,
          correct_percentage: 6 / 7,
          first_asked_at: '2026-03-30T07:00:00Z',
          last_asked_at: null,
          accepted_answers: [['ottawa']],
          schedule: {
            bucket: 'due_review',
            logical_bucket: '3h',
            interval_step: 1,
            last_incorrect_at: '2026-04-01T08:00:00Z',
            next_due_at: '2026-04-07T08:00:00Z'
          }
        }),
        buildQuestionRow({
          question_id: 52,
          module_id: 5,
          module_full_slug: 'geography/capitals',
          prompt: 'What is the capital of Sweden?',
          prompt_preview: 'What is the capital of Sweden?',
          rank: 6,
          attempts: 2,
          correct_percentage: 1,
          first_asked_at: '2026-04-02T07:30:00Z',
          last_asked_at: '2026-04-02T07:30:00Z',
          accepted_answers: [['stockholm']],
          schedule: {
            bucket: 'mastery',
            logical_bucket: 'mastery'
          }
        }),
        buildQuestionRow({
          question_id: 53,
          module_id: 3,
          module_full_slug: 'biology/plants',
          prompt: 'What process lets plants turn light into stored energy?',
          prompt_preview: 'What process lets plants turn light into stored energy?',
          rank: 1,
          attempts: 2,
          correct_percentage: 1 / 2,
          first_asked_at: '2026-04-03T07:00:00Z',
          last_asked_at: '2026-04-03T07:00:00Z',
          review_flag: true,
          accepted_answers: [['photosynthesis']],
          recent_incorrect_answers: [
            {
              answer_text: 'respiration',
              count: 1,
              latest_answered_at: '2026-04-03T07:00:00Z'
            }
          ],
          schedule: {
            bucket: 'hot0',
            logical_bucket: 'review',
            recovery_streak: 0,
            interval_step: 0,
            last_incorrect_at: '2026-04-03T07:00:00Z',
            retry_pending: true
          }
        })
      ]
    });

    const view = render(StatsPage, {
      props: {
        moduleLabel: 'Biology',
        stats,
        loading: false,
        reviewOnly: false,
        onToggleReviewOnly: toggleSpy,
        onOpenCreate: vi.fn(),
        onOpenEdit: openSpy
      }
    });

    let mainPanel = screen.getByRole('heading', { name: 'Questions' }).closest('.panel') as HTMLElement;
    expect(screen.queryByText('What structure anchors most plants in the ground?')).toBeNull();
    expect(within(mainPanel).getByText('What is the capital of Canada?')).toBeTruthy();
    expect(within(mainPanel).getByText('What is the capital of Sweden?')).toBeTruthy();

    await user.click(within(mainPanel).getByText('What is the capital of Canada?'));
    expect(openSpy).toHaveBeenCalledWith(stats.questions[1]);

    await user.click(within(mainPanel).getByRole('button', { name: 'Bucket' }));
    await waitFor(() => {
      const rowsAfterScheduleSort = within(mainPanel).getAllByRole('row');
      expect(rowsAfterScheduleSort[1].textContent).toContain('What is the capital of Canada?');
      expect(rowsAfterScheduleSort[1].textContent).toContain('3h');
    });

    await user.click(within(mainPanel).getByRole('button', { name: 'Attempts' }));
    await waitFor(() => {
      const rowsAfterSort = within(mainPanel).getAllByRole('row');
      expect(rowsAfterSort[1].textContent).toContain('What is the capital of Canada?');
    });

    await user.click(screen.getByRole('checkbox'));
    expect(toggleSpy).toHaveBeenCalledWith(true);
    await view.rerender({
      moduleLabel: 'Biology',
      stats,
      loading: false,
      reviewOnly: true,
      onToggleReviewOnly: toggleSpy,
      onOpenCreate: vi.fn(),
      onOpenEdit: openSpy
    });

    mainPanel = screen.getByRole('heading', { name: 'Questions' }).closest('.panel') as HTMLElement;
    expect(within(mainPanel).getByText('What structure anchors most plants in the ground?')).toBeTruthy();
    expect(within(mainPanel).getByText('What process lets plants turn light into stored energy?')).toBeTruthy();
    expect(screen.queryByText('What is the capital of Canada?')).toBeNull();

    await user.click(within(mainPanel).getByText('What structure anchors most plants in the ground?'));
    expect(openSpy).toHaveBeenLastCalledWith(stats.questions[0]);

    expect(screen.getByRole('img', { name: 'Recent session accuracy graph' })).toBeTruthy();
    expect(screen.getByRole('img', { name: 'Spaced repetition stage counts' })).toBeTruthy();
    expect(screen.getByRole('img', { name: 'Entry state counts' })).toBeTruthy();
    expect(screen.getByRole('img', { name: 'Retry eligibility by day' })).toBeTruthy();
    expect(screen.getByRole('img', { name: 'First-time questions answered by day' })).toBeTruthy();
    expect(screen.getByRole('heading', { name: 'Latest quiz performance' }).closest('.stats-chart-panel-performance')).toBeTruthy();
    expect(screen.getByRole('heading', { name: 'Entry states' }).closest('.stats-chart-panel-entry')).toBeTruthy();
    expect(screen.getByRole('heading', { name: 'Spaced repetition stages' }).closest('.stats-chart-panel-stages')).toBeTruthy();
    expect(screen.getByRole('heading', { name: 'Retry eligibility' }).closest('.stats-chart-panel-retry')).toBeTruthy();
    expect(screen.getByRole('heading', { name: 'First-time questions answered' }).closest('.stats-chart-panel-first-seen')).toBeTruthy();

    const graphLabels = Array.from(view.container.querySelectorAll('.session-bar text')).map((node) => node.textContent);
    expect(graphLabels).toContain('2/3');
    expect(graphLabels).toContain('2/2');
    expect(graphLabels).toContain('Unseen');
    expect(graphLabels).toContain('Review');
    expect(graphLabels).toContain('Bucketed');
    expect(graphLabels).toContain('1h');
    expect(graphLabels).toContain('3h');
    expect(graphLabels).toContain('6h');
    expect(graphLabels).toContain('12h');
    expect(graphLabels).toContain('1d');
    expect(graphLabels).toContain('3d');
    expect(graphLabels).toContain('7d');
    expect(graphLabels).toContain('14d');
    expect(graphLabels).toContain('30d');
    expect(graphLabels).toContain('60d');
    expect(graphLabels).toContain('Mastery');
    expect(graphLabels).toContain('<1');
    expect(graphLabels).toContain('7');
    expect(graphLabels).toContain('>7');
    expect(view.container.querySelector('.graph-average-line title')?.textContent).toBe('83%');
    expect(screen.queryByRole('button', { name: 'Review' })).toBeNull();
    expect(screen.getByRole('button', { name: 'Open retry eligibility details' })).toBeTruthy();
    expect(within(mainPanel).getByRole('button', { name: 'Bucket' })).toBeTruthy();
    expect(within(mainPanel).getByRole('button', { name: 'Last seen' })).toBeTruthy();
    expect(screen.queryByRole('button', { name: 'Type' })).toBeNull();
    expect(screen.queryByRole('button', { name: 'Module' })).toBeNull();

    const firstRowClass =
      within(mainPanel).getByText('What structure anchors most plants in the ground?').closest('tr')?.className ?? '';
    expect(firstRowClass).toContain('flagged-review');
    expect(firstRowClass).not.toContain('hot1-row');

    await user.click(within(mainPanel).getByRole('button', { name: 'Last seen' }));
    await waitFor(() => {
      const rowsAfterLastSeenSort = within(mainPanel).getAllByRole('row');
      expect(rowsAfterLastSeenSort[1].textContent).toContain('What process lets plants turn light into stored energy?');
      expect(rowsAfterLastSeenSort[2].textContent).toContain('What structure anchors most plants in the ground?');
    });
  });

  it('opens the retry detail overlay from the retry graph and closes it again', async () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date('2026-04-05T10:30:00Z'));
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });

    const view = render(StatsPage, {
      props: {
        stats: buildStatsResponse({
          summary: {
            total_questions: 2,
            total_attempts: 2,
            total_correct: 2,
            total_possible: 2,
            accuracy: 1
          },
          questions: [
            buildQuestionRow({
              question_id: 1,
              prompt: 'due today',
              prompt_preview: 'due today',
              attempts: 1,
              correct_percentage: 1,
              first_asked_at: '2026-04-04T08:00:00Z',
              last_asked_at: '2026-04-04T08:00:00Z',
              schedule: {
                bucket: 'cooling',
                logical_bucket: '1d',
                interval_step: 4,
                next_due_at: '2026-04-05T23:00:00Z'
              }
            }),
            buildQuestionRow({
              question_id: 2,
              prompt: 'due in a month',
              prompt_preview: 'due in a month',
              attempts: 1,
              correct_percentage: 1,
              first_asked_at: '2026-04-04T08:00:00Z',
              last_asked_at: '2026-04-04T08:00:00Z',
              schedule: {
                bucket: 'cooling',
                logical_bucket: '30d',
                interval_step: 8,
                next_due_at: '2026-05-05T10:00:00Z'
              }
            })
          ]
        })
      }
    });

    await user.click(screen.getByRole('heading', { name: 'Retry eligibility' }));

    const dialog = screen.getByRole('dialog', { name: 'Retry eligibility details' });
    expect(dialog).toBeTruthy();
    expect(within(dialog).getByRole('img', { name: 'Retry eligibility under one day by hour' })).toBeTruthy();
    expect(within(dialog).getByRole('img', { name: 'Retry eligibility beyond seven days by week' })).toBeTruthy();
    expect(within(dialog).getByText('10:00')).toBeTruthy();

    await user.click(within(dialog).getByRole('button', { name: 'Close' }));
    await waitFor(() => {
      expect(screen.queryByRole('dialog', { name: 'Retry eligibility details' })).toBeNull();
    });

    await user.click(screen.getByRole('heading', { name: 'Retry eligibility' }));
    expect(screen.getByRole('dialog', { name: 'Retry eligibility details' })).toBeTruthy();

    const backdrop = view.container.querySelector('.retry-detail-backdrop');
    expect(backdrop).toBeTruthy();
    if (backdrop) {
      await user.click(backdrop);
    }
    await waitFor(() => {
      expect(screen.queryByRole('dialog', { name: 'Retry eligibility details' })).toBeNull();
    });
  });

  it('shows an empty review state when the toggle is on but no review questions exist', () => {
    render(StatsPage, {
      props: {
        stats: buildStatsResponse({
          summary: {
            total_questions: 1
          },
          questions: [
            buildQuestionRow({
              module_id: 2,
              module_full_slug: 'geography/capitals',
              prompt: 'What is the capital of Canada?',
              prompt_preview: 'What is the capital of Canada?',
              accepted_answers: [['ottawa']]
            })
          ]
        }),
        reviewOnly: true
      }
    });

    expect(screen.getByText('No review questions in this scope.')).toBeTruthy();
  });

  it('shows an empty main table when every question is review-flagged', () => {
    render(StatsPage, {
      props: {
        stats: buildStatsResponse({
          summary: {
            total_questions: 1,
            reviewed_questions: 1,
            total_attempts: 1,
            total_correct: 1,
            total_possible: 1,
            accuracy: 1
          },
          questions: [
            buildQuestionRow({
              module_id: 2,
              module_full_slug: 'biology/plants',
              prompt: 'What structure anchors most plants in the ground?',
              prompt_preview: 'What structure anchors most plants in the ground?',
              attempts: 1,
              correct_percentage: 1,
              first_asked_at: '2026-04-01T06:00:00Z',
              last_asked_at: '2026-04-01T06:00:00Z',
              review_flag: true,
              accepted_answers: [['roots']],
              schedule: {
                bucket: 'hot1_sit_out',
                logical_bucket: 'review',
                recovery_streak: 1,
                interval_step: 0,
                last_incorrect_at: '2026-04-01T06:00:00Z'
              }
            })
          ]
        })
      }
    });

    expect(screen.getByText('No non-review questions in this scope.')).toBeTruthy();
  });
});
