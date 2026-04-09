import './test-support';

import { render, screen } from '@testing-library/svelte';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import AdminPage from '../src/components/AdminPage.svelte';
import EditorDrawer from '../src/components/EditorDrawer.svelte';
import ImportDrawer from '../src/components/ImportDrawer.svelte';
import type { ModuleNode, QuestionImportResult } from '../src/lib/types';

describe('EditorDrawer', () => {
  it('shows type-specific ghost text in create mode', async () => {
    const user = userEvent.setup();
    const modules: ModuleNode[] = [
      {
        id: 1,
        title: 'Geography',
        slug: 'geography',
        full_slug: 'geography',
        instruction: '',
        children: []
      }
    ];

    render(EditorDrawer, {
      props: {
        open: true,
        modules,
        defaultModuleId: 1,
        editingQuestion: null,
        saving: false,
        onClose: vi.fn(),
        onSave: vi.fn()
      }
    });

    expect(screen.getByPlaceholderText('What is the capital of Norway?')).toBeTruthy();
    expect(screen.getByPlaceholderText('oslo')).toBeTruthy();

    await user.selectOptions(screen.getByLabelText('Question type'), 'multi_text');
    expect(screen.getByPlaceholderText('Name the two rivers that meet at Khartoum.')).toBeTruthy();
    expect(screen.getByPlaceholderText('white nile')).toBeTruthy();
    expect(screen.getByPlaceholderText('blue nile')).toBeTruthy();

    await user.selectOptions(screen.getByLabelText('Question type'), 'ordered_multi');
    expect(screen.getByPlaceholderText('Name the stages in order.')).toBeTruthy();
    expect(screen.getByPlaceholderText('stage one')).toBeTruthy();
    expect(screen.getByPlaceholderText('stage two')).toBeTruthy();

    await user.selectOptions(screen.getByLabelText('Question type'), 'inline_cloze');
    expect(screen.getByPlaceholderText('The [Amazon | Amazon River] flows through South America.')).toBeTruthy();
    expect(screen.getByPlaceholderText(/The derivative of/)).toBeTruthy();
    expect(screen.getByPlaceholderText('x^2')).toBeTruthy();
    expect(screen.getByPlaceholderText('.')).toBeTruthy();

    await user.selectOptions(screen.getByLabelText('Question type'), 'computed_text');
    expect(screen.getByPlaceholderText(/\$m=\[1-10\]\*100\$/)).toBeTruthy();
    expect(screen.getByPlaceholderText('$m/v$ ml')).toBeTruthy();
    expect(screen.getByText('QML')).toBeTruthy();
  });

  it('shows dense revision fields and aggregated incorrect answers without duplicate module UI', () => {
    const modules: ModuleNode[] = [
      {
        id: 1,
        title: 'Norwegian',
        slug: 'norwegian',
        full_slug: 'norwegian',
        instruction: '',
        children: [
          {
            id: 2,
            title: 'Vocabulary',
            slug: 'vocabulary',
            full_slug: 'norwegian/vocabulary',
            instruction: '',
            children: [
              {
                id: 3,
                title: 'noun2en',
                slug: 'noun2en',
                full_slug: 'norwegian/vocabulary/noun2en',
                instruction: 'Translate the Norwegian term into English.',
                children: []
              }
            ]
          }
        ]
      }
    ];

    render(EditorDrawer, {
      props: {
        open: true,
        modules,
        editingQuestion: {
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
          review_flag: true,
          accepted_answers: [['dog']],
          segments: [],
          schedule: {
            bucket: 'hot0',
            logical_bucket: 'unseen',
            recovery_streak: 0,
            interval_step: 0,
            last_incorrect_at: '2026-04-04T08:00:00Z',
            next_due_at: null,
            retry_pending: false
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
        },
        saving: false,
        onClose: vi.fn(),
        onSave: vi.fn()
      }
    });

    expect(screen.getByText('Previously incorrect answers')).toBeTruthy();
    expect(screen.getByText('hound')).toBeTruthy();
    expect(screen.getByText('puppy')).toBeTruthy();
    expect(screen.getByText('3')).toBeTruthy();
    expect(screen.getByText('1')).toBeTruthy();
    expect(screen.getByText('Module')).toBeTruthy();
    expect(screen.queryByText('Module path')).toBeNull();
    expect(screen.queryByText('Create module inline')).toBeNull();
    expect(screen.queryByText('Flag this question for manual review')).toBeNull();
  });
});

describe('AdminPage', () => {
  it('creates users from admin, creates a module, and offers leaf-module import', async () => {
    const user = userEvent.setup();
    const createUserSpy = vi.fn().mockResolvedValue({
      id: 9,
      handle: 'ignazio',
      display_name: 'Ignazio',
      created_at: '2026-04-05T10:00:00Z'
    });
    const createSpy = vi.fn().mockResolvedValue({
      id: 8,
      title: 'Norwegian',
      slug: 'norwegian',
      full_slug: 'norwegian',
      instruction: 'Translate the Norwegian term into English.',
      children: []
    });
    const openImportSpy = vi.fn();
    const modules: ModuleNode[] = [
      {
        id: 1,
        title: 'Nursing',
        slug: 'nursing',
        full_slug: 'nursing',
        instruction: '',
        children: [
          {
            id: 2,
            title: 'Checks',
            slug: 'checks',
            full_slug: 'nursing/checks',
            instruction: 'List the safety checks in order.',
            children: []
          },
          {
            id: 3,
            title: 'Definitions',
            slug: 'definitions',
            full_slug: 'nursing/definitions',
            instruction: 'Define the nursing term in plain language.',
            children: []
          }
        ]
      }
    ];

    render(AdminPage, {
      props: {
        modules,
        users: [],
        activeUser: null,
        selectedModuleId: 2,
        onCreateUser: createUserSpy,
        onCreateModule: createSpy,
        onOpenImport: openImportSpy
      }
    });

    expect(screen.queryByText('Current modules')).toBeNull();
    expect(screen.getByRole('heading', { name: 'Create Module Path' })).toBeTruthy();
    expect(screen.getByRole('heading', { name: 'Create User' })).toBeTruthy();
    expect(screen.getByRole('heading', { name: 'Import QML' })).toBeTruthy();
    expect(screen.queryByText('Users')).toBeNull();
    expect(screen.queryByText('Question import')).toBeNull();
    expect(screen.getAllByText(/Imports will create questions directly in/).length).toBeGreaterThan(0);

    expect(screen.getByRole('button', { name: 'Create Module' }).className).toContain('primary-button');
    expect(screen.getByRole('button', { name: 'Create User' }).className).toContain('primary-button');
    expect(screen.getByRole('button', { name: 'Import QML' }).className).toContain('primary-button');

    await user.type(screen.getByPlaceholderText('ignazio'), 'ignazio');
    await user.type(screen.getByPlaceholderText('Ignazio'), 'Ignazio');
    await user.click(screen.getByRole('button', { name: 'Create User' }));
    expect(createUserSpy).toHaveBeenCalledWith({
      handle: 'ignazio',
      display_name: 'Ignazio'
    });
    expect(await screen.findByText('User ready: Ignazio.')).toBeTruthy();

    const selects = screen.getAllByRole('combobox');
    await user.selectOptions(selects[1], '3');
    await user.click(screen.getByRole('button', { name: 'Import QML' }));
    expect(openImportSpy).toHaveBeenCalledWith(3);

    await user.type(screen.getByPlaceholderText('norwegian/vocabulary/nouns_to_english'), 'Vocabulary');
    await user.selectOptions(selects[0], '1');
    await user.type(
      screen.getByPlaceholderText('Translate each Norwegian noun into English.'),
      'Use the Norwegian term as the prompt.'
    );
    await user.click(screen.getByRole('button', { name: 'Create Module' }));

    expect(createSpy).toHaveBeenCalledWith({
      title: 'Vocabulary',
      parent_id: 1,
      instruction: 'Use the Norwegian term as the prompt.'
    });

    expect(await screen.findByText('Module path ready: norwegian.')).toBeTruthy();
  });
});

describe('ImportDrawer', () => {
  it('revalidates edited unresolved rows, supports discard, and returns to the start state after commit', async () => {
    const user = userEvent.setup();
    const revalidateSpy = vi.fn().mockResolvedValue(undefined);
    const commitSpy = vi.fn().mockResolvedValue(undefined);
    const moduleNode: ModuleNode = {
      id: 12,
      title: 'noun2en',
      slug: 'noun2en',
      full_slug: 'norwegian/vocabulary/noun2en',
      instruction: 'Translate each Norwegian noun into English.',
      children: []
    };
    const result: QuestionImportResult = {
      ready_to_commit: false,
      valid_row_count: 2,
      skipped_duplicate_count: 1,
      skipped_rows: [
        {
          row_number: 1,
          qml_line: 'hund [dog]',
          reason: 'Prompt already exists in this leaf module.',
          inferred_type: 'single_text'
        }
      ],
      report_text: 'row 2 | needs fix | Question lines cannot be blank. | ',
      committed: false,
      committed_count: 0,
      unresolved_rows: [
        {
          row_number: 2,
          qml_line: 'ordered: stage one',
          issues: ['Question lines cannot be blank.'],
          inferred_type: null
        },
        {
          row_number: 4,
          qml_line: 'ordered: stage alpha',
          issues: ['Question lines cannot be blank.'],
          inferred_type: null
        }
      ]
    };

    const view = render(ImportDrawer, {
      props: {
        open: true,
        moduleNode,
        result,
        busy: false,
        onClose: vi.fn(),
        onStartImport: vi.fn(),
        onRevalidate: revalidateSpy,
        onCommit: commitSpy
      }
    });

    expect(screen.getByDisplayValue('ordered: stage one')).toBeTruthy();
    expect(screen.getByRole('button', { name: 'Discard row 2' })).toBeTruthy();

    const rowInputs = view.getAllByRole('textbox');
    const unresolvedInput = rowInputs.find(
      (input) => (input as HTMLInputElement).value === 'ordered: stage one'
    ) as HTMLInputElement;
    await user.clear(unresolvedInput);
    await user.type(unresolvedInput, 'ordered: stage one ; stage two');
    await user.click(screen.getByRole('button', { name: 'Revalidate Rows' }));

    expect(revalidateSpy).toHaveBeenCalledWith([
      { row_number: 1, qml_line: 'hund [dog]' },
      { row_number: 2, qml_line: 'ordered: stage one ; stage two' },
      { row_number: 4, qml_line: 'ordered: stage alpha' }
    ]);

    await user.click(screen.getByRole('button', { name: 'Discard row 4' }));
    expect(revalidateSpy).toHaveBeenLastCalledWith([
      { row_number: 1, qml_line: 'hund [dog]' },
      { row_number: 2, qml_line: 'ordered: stage one ; stage two' }
    ]);

    await view.rerender({
      open: true,
      moduleNode,
      result: {
        ...result,
        ready_to_commit: true,
        valid_row_count: 3,
        skipped_duplicate_count: 1,
        skipped_rows: result.skipped_rows,
        report_text: 'All remaining rows are valid. Commit to save them.',
        unresolved_rows: []
      },
      busy: false,
      onClose: vi.fn(),
      onStartImport: vi.fn(),
      onRevalidate: revalidateSpy,
      onCommit: commitSpy
    });

    expect(screen.queryByRole('button', { name: 'Discard row 2' })).toBeNull();
    await user.click(screen.getByRole('button', { name: 'Commit Import' }));
    expect(commitSpy).toHaveBeenCalledWith([
      { row_number: 1, qml_line: 'hund [dog]' },
      { row_number: 2, qml_line: 'ordered: stage one ; stage two' }
    ]);

    await view.rerender({
      open: true,
      moduleNode,
      result: null,
      busy: false,
      onClose: vi.fn(),
      onStartImport: vi.fn(),
      onRevalidate: revalidateSpy,
      onCommit: commitSpy
    });

    expect(screen.getByRole('button', { name: 'Start Import' })).toBeTruthy();
  });
});
