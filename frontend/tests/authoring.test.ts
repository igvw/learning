import { fireEvent, render, screen, waitFor, within } from '@testing-library/svelte';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import EditorDrawer from '../src/components/EditorDrawer.svelte';
import type { ModuleNode } from '../src/lib/types';
import { buildModuleNode, buildQuestionRow } from './builders';

describe('EditorDrawer', () => {
  it('shows type-specific ghost text in create mode', async () => {
    const user = userEvent.setup();
    const modules: ModuleNode[] = [buildModuleNode({ id: 1, title: 'Geography', slug: 'geography', full_slug: 'geography' })];

    const { container } = render(EditorDrawer, {
      props: {
        open: true,
        modules,
        defaultModuleId: 1,
        editingQuestion: null,
        saving: false,
        onClose: vi.fn(),
        onSave: vi.fn(),
        onDelete: vi.fn()
      }
    });

    expect(screen.queryByLabelText('Priority')).toBeNull();
    expect(screen.queryByLabelText('Rank')).toBeNull();
    expect(screen.getByPlaceholderText('What is another name for sodium chloride?')).toBeTruthy();
    expect(screen.getByPlaceholderText('sodium chloride | table salt')).toBeTruthy();
    expect(screen.getByText(/Answers are case-insensitive/)).toBeTruthy();
    const topRow = container.querySelector('.editor-top-row');
    expect(topRow?.textContent).toContain('Module');
    expect(topRow?.textContent).toContain('Question type');
    expect(topRow?.textContent).not.toContain('Prompt');
    expect(within(screen.getByLabelText('Question type')).getAllByRole('option').map((option) => option.getAttribute('value'))).toEqual([
      'single_text',
      'multi_text',
      'ordered_multi',
      'inline_cloze',
      'bundle'
    ]);

    await user.selectOptions(screen.getByLabelText('Question type'), 'multi_text');
    expect(screen.getByPlaceholderText('Name two primary colors.')).toBeTruthy();
    expect(screen.getByPlaceholderText('red')).toBeTruthy();
    expect(screen.getByPlaceholderText('blue')).toBeTruthy();

    await user.selectOptions(screen.getByLabelText('Question type'), 'ordered_multi');
    expect(screen.getByPlaceholderText('Name the first two stages in order.')).toBeTruthy();
    expect(screen.getByPlaceholderText('prophase')).toBeTruthy();
    expect(screen.getByPlaceholderText('metaphase')).toBeTruthy();

    await user.selectOptions(screen.getByLabelText('Question type'), 'inline_cloze');
    expect(screen.getByPlaceholderText('The [heart] pumps [blood] through the body.')).toBeTruthy();

    await user.selectOptions(screen.getByLabelText('Question type'), 'bundle');
    expect(screen.getByText('Bundle QML')).toBeTruthy();
    expect(screen.getByPlaceholderText(/A patient needs \{\}/)).toBeTruthy();
  });

  it('shows dense revision fields and aggregated incorrect answers without duplicate module UI', () => {
    const modules: ModuleNode[] = [
      buildModuleNode({
        id: 1,
        title: 'Norwegian',
        slug: 'norwegian',
        full_slug: 'norwegian',
        children: [
          buildModuleNode({
            id: 2,
            title: 'Vocabulary',
            slug: 'vocabulary',
            full_slug: 'norwegian/vocabulary',
            children: [
              buildModuleNode({
                id: 3,
                title: 'noun2en',
                slug: 'noun2en',
                full_slug: 'norwegian/vocabulary/noun2en',
                instruction: 'Translate the Norwegian term into English.'
              })
            ]
          })
        ]
      })
    ];

    render(EditorDrawer, {
      props: {
        open: true,
        modules,
        editingQuestion: buildQuestionRow({
          question_id: 30,
          module_id: 3,
          module_full_slug: 'norwegian/vocabulary/noun2en',
          prompt: 'hund',
          prompt_preview: 'hund',
          question_type: 'single_text',
          rank: 1,
          attempts: 4,
          correct_percentage: 0.5,
          last_asked_at: '2026-04-04T09:00:00Z',
          accepted_answers: [['dog']],
          segments: [],
          schedule: {
            bucket: 'hot0',
            logical_bucket: 'unseen',
            recovery_streak: 0,
            interval_step: 0,
            last_incorrect_at: '2026-04-04T08:00:00Z',
            next_due_at: null
          },
          recent_incorrect_answers: [
            {
              answer_text: 'hound',
              count: 3,
              latest_answered_at: '2026-04-04T08:00:00Z'
            },
            {
              answer_text: 'puppy',
              count: 1,
              latest_answered_at: '2026-04-03T08:00:00Z'
            }
          ]
        }),
        saving: false,
        onClose: vi.fn(),
        onSave: vi.fn(),
        onDelete: vi.fn()
      }
    });

    expect(screen.getByText('Previously incorrect answers')).toBeTruthy();
    expect(screen.getByText('hound')).toBeTruthy();
    expect(screen.getByText('puppy')).toBeTruthy();
    expect(screen.getByText('3')).toBeTruthy();
    expect(screen.getByText('1')).toBeTruthy();
    expect(screen.getByText('Module')).toBeTruthy();
    expect(screen.queryByLabelText('Rank')).toBeNull();
    expect(screen.queryByText('Module path')).toBeNull();
    expect(screen.queryByText('Create module inline')).toBeNull();
    expect(screen.queryByText('Flag this question for manual review')).toBeNull();
  });

  it('offers question deletion in revision mode and confirms before calling the handler', async () => {
    const user = userEvent.setup();
    const deleteSpy = vi.fn().mockResolvedValue(undefined);
    const confirmSpy = vi.spyOn(window, 'confirm').mockReturnValue(true);
    const modules: ModuleNode[] = [
      buildModuleNode({
        id: 1,
        title: 'Norwegian',
        slug: 'norwegian',
        full_slug: 'norwegian',
        children: [
          buildModuleNode({
            id: 2,
            title: 'Vocabulary',
            slug: 'vocabulary',
            full_slug: 'norwegian/vocabulary',
            children: [
              buildModuleNode({
                id: 3,
                title: 'weekday2en',
                slug: 'weekday2en',
                full_slug: 'norwegian/vocabulary/weekday2en',
                instruction: 'Translate the weekday into English.'
              })
            ]
          })
        ]
      })
    ];

    render(EditorDrawer, {
      props: {
        open: true,
        modules,
        editingQuestion: buildQuestionRow({
          question_id: 41,
          module_id: 3,
          module_full_slug: 'norwegian/vocabulary/weekday2en',
          prompt: 'lørdag',
          prompt_preview: 'lørdag',
          question_type: 'single_text',
          rank: 1,
          attempts: 2,
          correct_percentage: 0.5,
          last_asked_at: '2026-04-05T09:00:00Z',
          accepted_answers: [['Saturday']],
          segments: [],
          schedule: {
            bucket: 'hot0',
            logical_bucket: 'unseen',
            recovery_streak: 0,
            interval_step: 0,
            last_incorrect_at: '2026-04-05T08:00:00Z',
            next_due_at: null
          },
          recent_incorrect_answers: []
        }),
        saving: false,
        deleting: false,
        onClose: vi.fn(),
        onSave: vi.fn(),
        onDelete: deleteSpy
      }
    });

    await user.click(screen.getByRole('button', { name: 'Request Delete' }));

    expect(confirmSpy).toHaveBeenCalledWith('Request deletion for this verified question?');
    expect(deleteSpy).toHaveBeenCalledWith(41);

    confirmSpy.mockRestore();
  });

  it('derives inline cloze answer fields from QML and keeps them synchronized', async () => {
    const user = userEvent.setup();
    const modules: ModuleNode[] = [buildModuleNode({ id: 1, title: 'Geography', slug: 'geography', full_slug: 'geography' })];

    render(EditorDrawer, {
      props: {
        open: true,
        modules,
        defaultModuleId: 1,
        editingQuestion: null,
        saving: false,
        onClose: vi.fn(),
        onSave: vi.fn(),
        onDelete: vi.fn()
      }
    });

    await user.selectOptions(screen.getByLabelText('Question type'), 'inline_cloze');
    const qmlInput = screen.getByLabelText('QML');
    await fireEvent.input(qmlInput, { target: { value: 'The [heart] pumps [blood].' } });

    const firstBlank = await screen.findByLabelText('Blank 1 accepted answers');
    const secondBlank = await screen.findByLabelText('Blank 2 accepted answers');
    expect((firstBlank as HTMLTextAreaElement).value).toBe('heart');
    expect((secondBlank as HTMLTextAreaElement).value).toBe('blood');

    await user.clear(secondBlank);
    await user.type(secondBlank, 'blood | plasma');

    await waitFor(() => {
      expect((screen.getByLabelText('QML') as HTMLTextAreaElement).value).toBe('The [heart] pumps [blood | plasma].');
    });
  });

  it('shows unwrapped bundle QML in the editor and saves wrapped canonical bundle QML', async () => {
    const user = userEvent.setup();
    const saveSpy = vi.fn().mockResolvedValue(undefined);
    const modules: ModuleNode[] = [buildModuleNode({ id: 1, title: 'Geography', slug: 'geography', full_slug: 'geography' })];

    render(EditorDrawer, {
      props: {
        open: true,
        modules,
        defaultModuleId: 1,
        editingQuestion: null,
        saving: false,
        onClose: vi.fn(),
        onSave: saveSpy,
        onDelete: vi.fn()
      }
    });

    await user.click(screen.getByRole('button', { name: 'Module' }));
    await user.click(await screen.findByRole('button', { name: 'Geography' }));
    await user.selectOptions(screen.getByLabelText('Question type'), 'bundle');

    const bundleInput = screen.getByLabelText('Bundle QML');
    await fireEvent.input(bundleInput, {
      target: {
        value:
          'A patient needs {} mg of active ingredient. The medication has {} mg/ml of active ingredient. How much medication does the patient need? []\n {400} {20} [20]'
      }
    });

    expect((await screen.findByLabelText('Bundle row 1 parameter 1') as HTMLTextAreaElement).value).toBe('400');
    expect((screen.getByLabelText('Bundle row 1 parameter 2') as HTMLTextAreaElement).value).toBe('20');

    const answersField = screen.getByLabelText('Bundle row 1 accepted answers');
    await user.clear(answersField);
    await user.type(answersField, '20 | 20.0');

    await user.click(screen.getByRole('button', { name: 'Create Question' }));

    await waitFor(() => {
      expect(saveSpy).toHaveBeenCalledWith(
        {
          module_id: 1,
          prompt: '',
          question_type: 'bundle',
          rank: 1,
          accepted_answers: [],
          segments: [],
          bundle_qml:
            '{A patient needs {} mg of active ingredient. The medication has {} mg/ml of active ingredient. How much medication does the patient need? []\n {400} {20} [20 | 20.0]}'
        },
        true
      );
    });
  });

  it('closes the module picker when clicking elsewhere in the drawer', async () => {
    const user = userEvent.setup();
    const modules: ModuleNode[] = [buildModuleNode({ id: 1, title: 'Geography', slug: 'geography', full_slug: 'geography' })];

    render(EditorDrawer, {
      props: {
        open: true,
        modules,
        defaultModuleId: 1,
        editingQuestion: null,
        saving: false,
        onClose: vi.fn(),
        onSave: vi.fn(),
        onDelete: vi.fn()
      }
    });

    await user.click(screen.getByRole('button', { name: 'Module' }));
    expect(await screen.findByRole('dialog', { name: 'Module selection tree' })).toBeTruthy();

    await user.click(screen.getByLabelText('Question type'));

    await waitFor(() => {
      expect(screen.queryByRole('dialog', { name: 'Module selection tree' })).toBeNull();
    });
  });
});
