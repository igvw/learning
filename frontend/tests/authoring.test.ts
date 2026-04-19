import { fireEvent, render, screen, waitFor } from '@testing-library/svelte';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import AdminPage from '../src/components/AdminPage.svelte';
import EditorDrawer from '../src/components/EditorDrawer.svelte';
import ImportDrawer from '../src/components/ImportDrawer.svelte';
import ModerationQueuePanel from '../src/components/admin/ModerationQueuePanel.svelte';
import type { ModuleNode, QuestionImportResult } from '../src/lib/types';
import { buildAuthActor, buildModerationQueue, buildModuleNode, buildQuestionRow } from './builders';

describe('EditorDrawer', () => {
  it('shows type-specific ghost text in create mode', async () => {
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
          review_flag: true,
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
          review_flag: false,
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
});

describe('AdminPage', () => {
  it('creates users from admin, updates the selected leaf module, creates a module, and offers leaf-module import', async () => {
    const user = userEvent.setup();
    const createUserSpy = vi.fn().mockResolvedValue({
      id: 10,
      handle: 'alice',
      display_name: 'Alice',
      role: 'user',
      created_at: '2026-04-05T10:00:00Z'
    });
    const createSpy = vi.fn().mockResolvedValue(
      buildModuleNode({
        id: 8,
        title: 'Norwegian',
        slug: 'norwegian',
        full_slug: 'norwegian',
        instruction: 'Translate the Norwegian term into English.'
      })
    );
    const updateSpy = vi.fn().mockResolvedValue(
      buildModuleNode({
        id: 2,
        title: 'Safety Checks',
        slug: 'safety_checks',
        full_slug: 'nursing/safety_checks',
        instruction: 'List each safety check before continuing.'
      })
    );
    const updateRoleSpy = vi.fn().mockResolvedValue({
      id: 9,
      handle: 'ignazio',
      display_name: 'Ignazio',
      role: 'admin',
      created_at: '2026-04-05T10:00:00Z'
    });
    const updatePasswordSpy = vi.fn().mockResolvedValue(undefined);
    const openImportSpy = vi.fn();
    const modules: ModuleNode[] = [
      buildModuleNode({
        id: 1,
        title: 'Nursing',
        slug: 'nursing',
        full_slug: 'nursing',
        children: [
          buildModuleNode({
            id: 2,
            title: 'Checks',
            slug: 'checks',
            full_slug: 'nursing/checks',
            instruction: 'List the safety checks in order.'
          }),
          buildModuleNode({
            id: 3,
            title: 'Definitions',
            slug: 'definitions',
            full_slug: 'nursing/definitions',
            instruction: 'Define the nursing term in plain language.'
          })
        ]
      })
    ];

    render(AdminPage, {
      props: {
        currentActor: buildAuthActor({ handle: 'admin', display_name: 'Admin', role: 'admin' }),
        modules,
        users: [{ id: 9, handle: 'ignazio', display_name: 'Ignazio', role: 'user', created_at: '2026-04-05T10:00:00Z' }],
        selectedModuleId: 2,
        moderationQueue: { pending_modules: [], pending_questions: [], pending_revisions: [] },
        onCreateUser: createUserSpy,
        onUpdateUserRole: updateRoleSpy,
        onUpdateUserPassword: updatePasswordSpy,
        onCreateModule: createSpy,
        onUpdateModule: updateSpy,
        onOpenImport: openImportSpy
      }
    });

    expect(screen.getByRole('heading', { name: 'Catalog and moderation' })).toBeTruthy();
    expect(screen.getByRole('heading', { name: 'Accounts' })).toBeTruthy();
    expect(screen.getByRole('heading', { name: 'Modules' })).toBeTruthy();
    expect(screen.getByRole('heading', { name: 'Import QML' })).toBeTruthy();
    expect(screen.getByText('Selected leaf module')).toBeTruthy();
    expect(screen.getByText('Create module')).toBeTruthy();
    expect(screen.queryByText('Current modules')).toBeNull();

    expect(screen.getByRole('button', { name: 'Save Module' }).className).toContain('primary-button');
    expect(screen.getByRole('button', { name: 'Create Module' }).className).toContain('primary-button');
    expect(screen.getByRole('button', { name: 'Create Account' }).className).toContain('primary-button');
    expect(screen.getByRole('button', { name: 'Save Role' }).className).toContain('primary-button');
    expect(screen.getByRole('button', { name: 'Import QML' }).className).toContain('primary-button');

    const titleInput = screen.getByDisplayValue('Checks');
    await user.clear(titleInput);
    await user.type(titleInput, 'Safety Checks');
    const editInstruction = screen.getByDisplayValue('List the safety checks in order.');
    await user.clear(editInstruction);
    await user.type(editInstruction, 'List each safety check before continuing.');
    await user.click(screen.getByRole('button', { name: 'Save Module' }));

    expect(updateSpy).toHaveBeenCalledWith(2, {
      title: 'Safety Checks',
      instruction: 'List each safety check before continuing.'
    });
    expect(await screen.findByText('Module ready: nursing/safety_checks.')).toBeTruthy();

    const confirmPasswordInputs = screen.getAllByLabelText('Confirm password');
    await user.type(screen.getByLabelText('Username'), 'alice');
    await user.type(screen.getByLabelText('Display name'), 'Alice');
    await user.type(screen.getByLabelText('Password'), 'password123');
    await user.type(confirmPasswordInputs[0], 'password999');
    expect((screen.getByRole('button', { name: 'Create Account' }) as HTMLButtonElement).disabled).toBe(true);
    expect(screen.getByText('Passwords must match before creating an account.')).toBeTruthy();
    await user.clear(confirmPasswordInputs[0]);
    await user.type(confirmPasswordInputs[0], 'password123');
    await user.click(screen.getByRole('button', { name: 'Create Account' }));
    expect(createUserSpy).toHaveBeenCalledWith({
      handle: 'alice',
      display_name: 'Alice',
      role: 'user',
      password: 'password123'
    });
    expect(await screen.findByText('Account ready: Alice.')).toBeTruthy();

    await user.selectOptions(screen.getByLabelText('Manage account'), '9');
    await user.selectOptions(screen.getAllByLabelText('Role')[1], 'admin');
    await user.click(screen.getByRole('button', { name: 'Save Role' }));
    expect(updateRoleSpy).toHaveBeenCalledWith(9, 'admin');
    expect(await screen.findByText('Role updated for Ignazio.')).toBeTruthy();

    await user.type(screen.getByLabelText('New password'), 'new-password123');
    await user.type(confirmPasswordInputs[1], 'new-password999');
    expect((screen.getByRole('button', { name: 'Update Password' }) as HTMLButtonElement).disabled).toBe(true);
    expect(screen.getByText('Passwords must match before updating a password.')).toBeTruthy();
    await user.clear(confirmPasswordInputs[1]);
    await user.type(confirmPasswordInputs[1], 'new-password123');
    await user.click(screen.getByRole('button', { name: 'Update Password' }));
    expect(updatePasswordSpy).toHaveBeenCalledWith(9, 'new-password123');
    expect(await screen.findByText('Password updated.')).toBeTruthy();

    await user.selectOptions(screen.getByLabelText('Import target'), '3');
    await user.click(screen.getByRole('button', { name: 'Import QML' }));
    expect(openImportSpy).toHaveBeenCalledWith(3);

    await user.type(screen.getByPlaceholderText('norwegian/vocabulary/nouns_to_english'), 'Vocabulary');
    await user.selectOptions(screen.getByLabelText('Parent module'), '1');
    await user.type(screen.getAllByLabelText('Instruction')[1], 'Use the Norwegian term as the prompt.');
    await user.click(screen.getByRole('button', { name: 'Create Module' }));

    expect(createSpy).toHaveBeenCalledWith({
      title: 'Vocabulary',
      parent_id: 1,
      instruction: 'Use the Norwegian term as the prompt.'
    });

    expect(await screen.findByText('Module ready: norwegian.')).toBeTruthy();
  });
});

describe('ModerationQueuePanel', () => {
  it('shows summary cards, opens overlays, and supports bulk approve by module', async () => {
    const user = userEvent.setup();
    const moderationSpy = vi.fn().mockResolvedValue(undefined);
    const bulkSpy = vi.fn().mockResolvedValue({ succeeded: 2, failed: 0 });

    render(ModerationQueuePanel, {
      props: {
        moderationQueue: buildModerationQueue({
          pending_modules: [
            {
              id: 7,
              title: 'Vocabulary',
              full_slug: 'norwegian/vocabulary',
              parent_id: 1,
              instruction: 'Translate the Norwegian term into English.',
              admin_verified: false,
              moderation_status: 'pending',
              created_by_user_id: 2,
              creator_display_name: 'Alice',
              admin_review_note: ''
            }
          ],
          pending_questions: [
            {
              question_id: 11,
              module_id: 3,
              module_full_slug: 'norwegian/vocabulary/noun2en',
              prompt: 'hund',
              question_type: 'single_text',
              rank: 1,
              accepted_answers: [['dog']],
              segments: [],
              admin_verified: false,
              moderation_status: 'pending',
              created_by_user_id: 2,
              creator_display_name: 'Alice',
              admin_review_note: ''
            },
            {
              question_id: 12,
              module_id: 3,
              module_full_slug: 'norwegian/vocabulary/noun2en',
              prompt: 'katt',
              question_type: 'single_text',
              rank: 2,
              accepted_answers: [['cat']],
              segments: [],
              admin_verified: false,
              moderation_status: 'pending',
              created_by_user_id: 2,
              creator_display_name: 'Alice',
              admin_review_note: ''
            }
          ],
          pending_revisions: [
            {
              proposal_id: 21,
              question_id: 5,
              proposer_user_id: 3,
              proposer_display_name: 'Bob',
              status: 'pending',
              delete_requested: false,
              admin_review_note: '',
              module_id: 3,
              module_full_slug: 'norwegian/vocabulary/noun2en',
              current_prompt: 'dag',
              current_question_type: 'single_text',
              current_accepted_answers: [['day']],
              current_segments: [],
              proposed_prompt: 'dagen',
              proposed_question_type: 'single_text',
              proposed_accepted_answers: [['the day']],
              proposed_segments: []
            }
          ]
        }),
        onModerationAction: moderationSpy,
        onBulkQuestionModeration: bulkSpy
      }
    });

    expect(screen.getByRole('button', { name: /Pending modules/i })).toBeTruthy();
    expect(screen.getByRole('button', { name: /Pending uploaded questions/i })).toBeTruthy();
    expect(screen.getByRole('button', { name: /Pending revisions/i })).toBeTruthy();

    await user.click(screen.getByRole('button', { name: /Pending modules/i }));
    expect(screen.getByRole('heading', { name: 'Pending modules' })).toBeTruthy();
    await user.click(screen.getByRole('button', { name: 'Close' }));

    await user.click(screen.getByRole('button', { name: /Pending revisions/i }));
    expect(screen.getByRole('heading', { name: 'Pending revisions' })).toBeTruthy();
    await user.click(screen.getByRole('button', { name: 'Close' }));

    await user.click(screen.getByRole('button', { name: /Pending uploaded questions/i }));
    expect(screen.getByRole('heading', { name: 'Pending uploaded questions' })).toBeTruthy();
    expect(screen.getByText('norwegian/vocabulary/noun2en')).toBeTruthy();

    await user.click(screen.getByLabelText('Select all pending questions in norwegian/vocabulary/noun2en'));
    await user.click(screen.getByRole('button', { name: 'Approve selected' }));

    expect(bulkSpy).toHaveBeenCalledWith([11, 12], { action: 'approve', note: '' });
    expect(await screen.findByText('Approved 2 questions.')).toBeTruthy();

    await user.click(screen.getAllByRole('button', { name: 'Request changes' })[0]);
    expect(moderationSpy).toHaveBeenCalledWith('question', 11, { action: 'changes_requested', note: '' });
  });

  it('reports partial bulk failures without removing the remaining selection', async () => {
    const user = userEvent.setup();
    const bulkSpy = vi.fn().mockResolvedValue({ succeeded: 1, failed: 1 });

    render(ModerationQueuePanel, {
      props: {
        moderationQueue: buildModerationQueue({
          pending_questions: [
            {
              question_id: 31,
              module_id: 9,
              module_full_slug: 'science/chemistry',
              prompt: 'H2O',
              question_type: 'single_text',
              rank: 1,
              accepted_answers: [['water']],
              segments: [],
              admin_verified: false,
              moderation_status: 'pending',
              created_by_user_id: 4,
              creator_display_name: 'Chris',
              admin_review_note: ''
            },
            {
              question_id: 32,
              module_id: 9,
              module_full_slug: 'science/chemistry',
              prompt: 'NaCl',
              question_type: 'single_text',
              rank: 2,
              accepted_answers: [['salt']],
              segments: [],
              admin_verified: false,
              moderation_status: 'pending',
              created_by_user_id: 4,
              creator_display_name: 'Chris',
              admin_review_note: ''
            }
          ]
        }),
        onModerationAction: vi.fn().mockResolvedValue(undefined),
        onBulkQuestionModeration: bulkSpy
      }
    });

    await user.click(screen.getByRole('button', { name: /Pending uploaded questions/i }));
    await user.click(screen.getByLabelText('Select all pending questions in science/chemistry'));
    await user.click(screen.getByRole('button', { name: 'Reject selected' }));

    expect(bulkSpy).toHaveBeenCalledWith([31, 32], { action: 'reject', note: '' });
    expect(await screen.findByText('Rejected 1 question. 1 could not be rejected.')).toBeTruthy();
    expect((screen.getByLabelText('Select pending question H2O') as HTMLInputElement).checked).toBe(true);
  });
});

describe('ImportDrawer', () => {
  it('submits edited rows through Save, shows blocking status, and removes rows locally', async () => {
    const user = userEvent.setup();
    const commitSpy = vi.fn().mockResolvedValue(undefined);
    const moduleNode: ModuleNode = buildModuleNode({
      id: 12,
      title: 'noun2en',
      slug: 'noun2en',
      full_slug: 'norwegian/vocabulary/noun2en',
      instruction: 'Translate each Norwegian noun into English.'
    });
    const result: QuestionImportResult = {
      ready_to_commit: false,
      rows: [
        { row_number: 1, qml_line: 'hund [dog]' },
        { row_number: 2, qml_line: 'ordered: stage one' },
        { row_number: 4, qml_line: 'mot [against | toward]' }
      ],
      valid_row_count: 2,
      exact_duplicate_count: 1,
      review_rows: [
        {
          row_number: 2,
          qml_line: 'ordered: stage one',
          status: 'invalid',
          status_text: 'Invalid QML: Question lines cannot be blank.',
          editable: true,
          blocking: true,
          current_answer_blocks: [],
          imported_answer_blocks: [],
          matched_questions: []
        },
        {
          row_number: 4,
          qml_line: 'mot [toward]',
          status: 'duplicate',
          status_text: 'This prompt already exists in the target leaf. Commit will revise the existing question in place unless you edit the row first.',
          editable: true,
          blocking: false,
          current_answer_blocks: ['against'],
          imported_answer_blocks: ['toward'],
          matched_questions: [
            {
              question_id: 8,
              module_id: 12,
              module_full_slug: 'norwegian/vocabulary/noun2en',
              qml_line: 'mot [against]',
              answer_blocks: ['against']
            }
          ]
        }
      ],
      report_text: '2 ready to commit | 2 rows need review | 1 exact duplicates omitted',
      committed: false,
      committed_count: 0
    };

    const view = render(ImportDrawer, {
      props: {
        open: true,
        moduleNode,
        result,
        busy: false,
        onClose: vi.fn(),
        onStartImport: vi.fn(),
        onCommit: commitSpy
      }
    });

    expect(document.querySelector('.import-drawer-shell')).toBeTruthy();
    expect(screen.getAllByText('norwegian/vocabulary/noun2en').length).toBeGreaterThan(0);
    expect(screen.getByText('2 review rows')).toBeTruthy();
    expect(screen.getByText('1 exact duplicates omitted')).toBeTruthy();
    expect(screen.getByText('Answers')).toBeTruthy();
    expect(screen.getByDisplayValue('ordered: stage one')).toBeTruthy();
    expect(screen.getByDisplayValue('mot [against]')).toBeTruthy();
    const invalidLine = screen.getByText('2');
    expect(invalidLine.className).toContain('status-invalid');
    expect(invalidLine.getAttribute('title')).toContain('Invalid QML');
    const currentAgainst = screen.getByRole('button', { name: 'Toggle current answer against in QML row 4' });
    const newToward = screen.getByRole('button', { name: 'Toggle imported answer toward in QML row 4' });
    expect(currentAgainst).toBeTruthy();
    expect(newToward).toBeTruthy();
    expect(currentAgainst.className).toContain('selected-answer-choice');
    expect(currentAgainst.className).toContain('source-current');
    expect(newToward.className).not.toContain('selected-answer-choice');
    expect(newToward.className).toContain('source-new');

    await user.click(newToward);
    expect((screen.getByDisplayValue('mot [against | toward]') as HTMLInputElement).value).toBe('mot [against | toward]');
    expect(screen.getByRole('button', { name: 'Toggle imported answer toward in QML row 4' }).className).toContain(
      'selected-answer-choice'
    );
    await user.click(screen.getByRole('button', { name: 'Toggle current answer against in QML row 4' }));
    expect((screen.getByDisplayValue('mot [toward]') as HTMLInputElement).value).toBe('mot [toward]');
    expect(screen.getByRole('button', { name: 'Toggle current answer against in QML row 4' }).className).not.toContain(
      'selected-answer-choice'
    );

    await fireEvent.input(screen.getByDisplayValue('mot [toward]'), { target: { value: 'mot [toward | opposite]' } });
    const manualOpposite = screen.getByRole('button', { name: 'Toggle manual answer opposite in QML row 4' });
    expect(manualOpposite).toBeTruthy();
    expect(manualOpposite.className).toContain('source-manual');
    expect(manualOpposite.className).toContain('selected-answer-choice');
    await user.click(manualOpposite);
    expect((screen.getByDisplayValue('mot [toward]') as HTMLInputElement).value).toBe('mot [toward]');

    const rowInputs = view.getAllByRole('textbox');
    const unresolvedInput = rowInputs.find(
      (input) => (input as HTMLInputElement).value === 'ordered: stage one'
    ) as HTMLInputElement;
    await user.clear(unresolvedInput);
    await user.type(unresolvedInput, 'ordered: stage one ; stage two');
    await user.click(screen.getByRole('button', { name: 'Save' }));

    expect(commitSpy).toHaveBeenCalledWith([
      { row_number: 1, qml_line: 'hund [dog]' },
      { row_number: 2, qml_line: 'ordered: stage one ; stage two' },
      { row_number: 4, qml_line: 'mot [toward]' }
    ]);

    await view.rerender({
      open: true,
      moduleNode,
      result,
      busy: false,
      onClose: vi.fn(),
      onStartImport: vi.fn(),
      onCommit: commitSpy
    });

    expect(screen.getByText('Fix the highlighted rows before saving.')).toBeTruthy();
    await user.click(screen.getByRole('button', { name: 'Remove row 4' }));
    expect(screen.queryByRole('button', { name: 'Remove row 4' })).toBeNull();
    expect(screen.queryByText('Fix the highlighted rows before saving.')).toBeNull();

    await view.rerender({
      open: true,
      moduleNode,
      result: {
        ...result,
        ready_to_commit: true,
        rows: [
          { row_number: 1, qml_line: 'hund [dog]' },
          { row_number: 2, qml_line: 'ordered: stage one ; stage two' }
        ],
        valid_row_count: 3,
        exact_duplicate_count: 1,
        review_rows: [],
        report_text: '3 ready to commit | 1 exact duplicates omitted'
      },
      busy: false,
      onClose: vi.fn(),
      onStartImport: vi.fn(),
      onCommit: commitSpy
    });

    expect(screen.queryByRole('button', { name: 'Remove row 2' })).toBeNull();
    await user.click(screen.getByRole('button', { name: 'Save' }));
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
      onCommit: commitSpy
    });

    expect(screen.getByRole('button', { name: 'Start Import' })).toBeTruthy();
    expect((screen.getByLabelText('Choose file') as HTMLInputElement).accept).toContain('.qml');
  });

  it('saves edited relocation rows directly without a separate revalidate step', async () => {
    const user = userEvent.setup();
    const commitSpy = vi.fn().mockResolvedValue(undefined);
    const moduleNode: ModuleNode = buildModuleNode({
      id: 20,
      title: 'target',
      slug: 'target',
      full_slug: 'norwegian/vocabulary/target',
      instruction: 'Target module.'
    });
    const result: QuestionImportResult = {
      ready_to_commit: true,
      rows: [{ row_number: 3, qml_line: 'hund [dog | canine | pooch]' }],
      valid_row_count: 1,
      exact_duplicate_count: 0,
      review_rows: [
        {
          row_number: 3,
          qml_line: 'hund [dog | canine | pooch]',
          target_module_full_slug: 'norwegian/vocabulary/target',
          status: 'relocation',
          status_text:
            'This prompt already exists in norwegian/vocabulary/source_a. Commit will move and revise that question in norwegian/vocabulary/target.',
          editable: true,
          blocking: false,
          current_answer_blocks: ['dog'],
          imported_answer_blocks: ['dog | canine | pooch'],
          matched_questions: [
            {
              question_id: 7,
              module_id: 4,
              module_full_slug: 'norwegian/vocabulary/source_a',
              qml_line: 'hund [dog]',
              answer_blocks: ['dog']
            }
          ]
        }
      ],
      report_text: '1 ready to commit | 1 rows need review',
      committed: false,
      committed_count: 0
    };

    render(ImportDrawer, {
      props: {
        open: true,
        moduleNode,
        result,
        busy: false,
        onClose: vi.fn(),
        onStartImport: vi.fn(),
        onCommit: commitSpy
      }
    });

    const currentAndNewDog = screen.getByRole('button', { name: 'Toggle current and imported answer dog in QML row 3' });
    expect(currentAndNewDog).toBeTruthy();
    expect(currentAndNewDog.className).toContain('selected-answer-choice');
    expect(currentAndNewDog.className).toContain('source-current-new');
    const relocationLine = screen.getByText('3');
    expect(relocationLine.getAttribute('title')).toContain('Commit will move and revise');

    const mergeInput = screen.getByDisplayValue('hund [dog]') as HTMLInputElement;
    await fireEvent.input(mergeInput, { target: { value: 'hund [dog | canine]' } });

    expect((screen.getByRole('button', { name: 'Save' }) as HTMLButtonElement).disabled).toBe(false);
    await user.click(screen.getByRole('button', { name: 'Save' }));
    expect(commitSpy).toHaveBeenCalledWith([{ row_number: 3, qml_line: 'hund [dog | canine]' }]);
  });

  it('shows an inline nothing-to-save message for exact-duplicate-only imports', async () => {
    const user = userEvent.setup();
    const commitSpy = vi.fn().mockResolvedValue(undefined);
    const moduleNode: ModuleNode = buildModuleNode({
      id: 30,
      title: 'target',
      slug: 'target',
      full_slug: 'norwegian/vocabulary/target',
      instruction: 'Target module.'
    });
    const result: QuestionImportResult = {
      ready_to_commit: false,
      rows: [{ row_number: 1, qml_line: 'år [year]' }],
      valid_row_count: 0,
      exact_duplicate_count: 1,
      review_rows: [],
      report_text: '1 exact duplicates omitted',
      committed: false,
      committed_count: 0
    };

    const view = render(ImportDrawer, {
      props: {
        open: true,
        moduleNode,
        result,
        busy: false,
        onClose: vi.fn(),
        onStartImport: vi.fn(),
        onCommit: commitSpy
      }
    });

    await user.click(screen.getByRole('button', { name: 'Save' }));
    expect(commitSpy).toHaveBeenCalledWith([{ row_number: 1, qml_line: 'år [year]' }]);

    await view.rerender({
      open: true,
      moduleNode,
      result,
      busy: false,
      onClose: vi.fn(),
      onStartImport: vi.fn(),
      onCommit: commitSpy
    });

    expect(screen.getByText('Nothing new to save.')).toBeTruthy();
  });

  it('publishes draft text and edited review rows so a parent can persist them', async () => {
    const user = userEvent.setup();
    const draftSpy = vi.fn();
    const moduleNode: ModuleNode = buildModuleNode({
      id: 31,
      title: 'target',
      slug: 'target',
      full_slug: 'norwegian/vocabulary/target',
      instruction: 'Target module.'
    });
    const result: QuestionImportResult = {
      ready_to_commit: true,
      rows: [{ row_number: 4, qml_line: 'mot [toward]' }],
      valid_row_count: 1,
      exact_duplicate_count: 0,
      review_rows: [
        {
          row_number: 4,
          qml_line: 'mot [toward]',
          status: 'duplicate',
          status_text: 'This prompt already exists in the target leaf.',
          editable: true,
          blocking: false,
          current_answer_blocks: ['against'],
          imported_answer_blocks: ['toward'],
          matched_questions: [
            {
              question_id: 8,
              module_id: 31,
              module_full_slug: 'norwegian/vocabulary/target',
              qml_line: 'mot [against]',
              answer_blocks: ['against']
            }
          ]
        }
      ],
      report_text: '1 row ready',
      committed: false,
      committed_count: 0
    };

    const view = render(ImportDrawer, {
      props: {
        open: true,
        moduleNode,
        result,
        busy: false,
        draftText: 'mot [toward]',
        draftRows: [{ row_number: 4, qml_line: 'mot [toward]' }],
        onClose: vi.fn(),
        onDraftChange: draftSpy,
        onStartImport: vi.fn(),
        onCommit: vi.fn()
      }
    });

    await user.click(screen.getByRole('button', { name: 'Toggle current answer against in QML row 4' }));
    expect(draftSpy).toHaveBeenLastCalledWith('mot [toward]', [{ row_number: 4, qml_line: 'mot [toward | against]' }]);

    await user.click(screen.getByRole('button', { name: 'Remove row 4' }));
    expect(draftSpy).toHaveBeenLastCalledWith('mot [toward]', []);

    await view.rerender({
      open: true,
      moduleNode,
      result: null,
      busy: false,
      draftText: 'år [year]',
      draftRows: [],
      onClose: vi.fn(),
      onDraftChange: draftSpy,
      onStartImport: vi.fn(),
      onCommit: vi.fn()
    });

    const qmlTextarea = screen.getByLabelText('QML text') as HTMLTextAreaElement;
    await fireEvent.input(qmlTextarea, { target: { value: 'selv [self]' } });
    await waitFor(() => {
      expect(draftSpy.mock.calls.some(([qmlText, rows]) => qmlText === 'selv [self]' && rows.length === 0)).toBe(true);
    });
  });

  it('keeps answer chips responsive when the parent echoes draft rows back after every click', async () => {
    const user = userEvent.setup();
    const moduleNode: ModuleNode = buildModuleNode({
      id: 32,
      title: 'target',
      slug: 'target',
      full_slug: 'norwegian/vocabulary/target',
      instruction: 'Target module.'
    });
    const result: QuestionImportResult = {
      ready_to_commit: true,
      rows: [{ row_number: 4, qml_line: 'mot [toward]' }],
      valid_row_count: 1,
      exact_duplicate_count: 0,
      review_rows: [
        {
          row_number: 4,
          qml_line: 'mot [toward]',
          status: 'duplicate',
          status_text: 'This prompt already exists in the target leaf.',
          editable: true,
          blocking: false,
          current_answer_blocks: ['against'],
          imported_answer_blocks: ['toward'],
          matched_questions: [
            {
              question_id: 8,
              module_id: 32,
              module_full_slug: 'norwegian/vocabulary/target',
              qml_line: 'mot [against]',
              answer_blocks: ['against']
            }
          ]
        }
      ],
      report_text: '1 row ready',
      committed: false,
      committed_count: 0
    };

    let echoedRows = [{ row_number: 4, qml_line: 'mot [against]' }];
    let view: ReturnType<typeof render> | null = null;
    const rerenderWithEcho = async (): Promise<void> => {
      if (!view) {
        return;
      }
      await view.rerender({
        open: true,
        moduleNode,
        result,
        busy: false,
        draftText: 'mot [toward]',
        draftRows: echoedRows,
        onClose: vi.fn(),
        onDraftChange: handleDraftChange,
        onStartImport: vi.fn(),
        onCommit: vi.fn()
      });
    };
    const handleDraftChange = (_qmlText: string, rows: { row_number: number; qml_line: string }[]): void => {
      echoedRows = rows.map((row) => ({ ...row }));
      void rerenderWithEcho();
    };

    view = render(ImportDrawer, {
      props: {
        open: true,
        moduleNode,
        result,
        busy: false,
        draftText: 'mot [toward]',
        draftRows: echoedRows,
        onClose: vi.fn(),
        onDraftChange: handleDraftChange,
        onStartImport: vi.fn(),
        onCommit: vi.fn()
      }
    });

    await user.click(screen.getByRole('button', { name: 'Toggle imported answer toward in QML row 4' }));
    await waitFor(() => {
      expect((screen.getByDisplayValue('mot [against | toward]') as HTMLInputElement).value).toBe('mot [against | toward]');
    });

    await user.click(screen.getByRole('button', { name: 'Toggle current answer against in QML row 4' }));
    await waitFor(() => {
      expect((screen.getByDisplayValue('mot [toward]') as HTMLInputElement).value).toBe('mot [toward]');
    });

    await user.click(screen.getByRole('button', { name: 'Toggle imported answer toward in QML row 4' }));
    await waitFor(() => {
      expect((screen.getByDisplayValue('mot []') as HTMLInputElement).value).toBe('mot []');
    });
  });
});
