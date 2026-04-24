import { fireEvent, render, screen, waitFor } from '@testing-library/svelte';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import ImportDrawer from '../src/components/ImportDrawer.svelte';
import type { ModuleNode, QuestionImportResult } from '../src/lib/types';
import { buildModuleNode } from './builders';

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
        { start_line: 1, end_line: 1, entry_kind: 'plain', qml_text: 'hund [dog]' },
        { start_line: 2, end_line: 2, entry_kind: 'plain', qml_text: 'ordered: stage one' },
        { start_line: 4, end_line: 4, entry_kind: 'plain', qml_text: 'mot [against | toward]' }
      ],
      valid_row_count: 2,
      exact_duplicate_count: 1,
      review_rows: [
        {
          start_line: 2,
          end_line: 2,
          entry_kind: 'plain',
          qml_text: 'ordered: stage one',
          status: 'invalid',
          status_text: 'Invalid QML: Question lines cannot be blank.',
          editable: true,
          blocking: true,
          current_answer_blocks: [],
          imported_answer_blocks: [],
          matched_questions: []
        },
        {
          start_line: 4,
          end_line: 4,
          entry_kind: 'plain',
          qml_text: 'mot [toward]',
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
              entry_kind: 'plain',
              qml_text: 'mot [against]',
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
      { start_line: 1, end_line: 1, entry_kind: 'plain', qml_text: 'hund [dog]' },
      { start_line: 2, end_line: 2, entry_kind: 'plain', qml_text: 'ordered: stage one ; stage two' },
      { start_line: 4, end_line: 4, entry_kind: 'plain', qml_text: 'mot [toward]' }
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
          { start_line: 1, end_line: 1, entry_kind: 'plain', qml_text: 'hund [dog]' },
          { start_line: 2, end_line: 2, entry_kind: 'plain', qml_text: 'ordered: stage one ; stage two' }
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
      { start_line: 1, end_line: 1, entry_kind: 'plain', qml_text: 'hund [dog]' },
      { start_line: 2, end_line: 2, entry_kind: 'plain', qml_text: 'ordered: stage one ; stage two' }
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
      rows: [{ start_line: 3, end_line: 3, entry_kind: 'plain', qml_text: 'hund [dog | canine | pooch]' }],
      valid_row_count: 1,
      exact_duplicate_count: 0,
      review_rows: [
        {
          start_line: 3,
          end_line: 3,
          entry_kind: 'plain',
          qml_text: 'hund [dog | canine | pooch]',
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
              entry_kind: 'plain',
              qml_text: 'hund [dog]',
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
    expect(commitSpy).toHaveBeenCalledWith([
      { start_line: 3, end_line: 3, entry_kind: 'plain', qml_text: 'hund [dog | canine]' }
    ]);
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
      rows: [{ start_line: 1, end_line: 1, entry_kind: 'plain', qml_text: 'år [year]' }],
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
    expect(commitSpy).toHaveBeenCalledWith([
      { start_line: 1, end_line: 1, entry_kind: 'plain', qml_text: 'år [year]' }
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
      rows: [{ start_line: 4, end_line: 4, entry_kind: 'plain', qml_text: 'mot [toward]' }],
      valid_row_count: 1,
      exact_duplicate_count: 0,
      review_rows: [
        {
          start_line: 4,
          end_line: 4,
          entry_kind: 'plain',
          qml_text: 'mot [toward]',
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
              entry_kind: 'plain',
              qml_text: 'mot [against]',
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
        draftRows: [{ start_line: 4, end_line: 4, entry_kind: 'plain', qml_text: 'mot [toward]' }],
        onClose: vi.fn(),
        onDraftChange: draftSpy,
        onStartImport: vi.fn(),
        onCommit: vi.fn()
      }
    });

    await user.click(screen.getByRole('button', { name: 'Toggle current answer against in QML row 4' }));
    expect(draftSpy).toHaveBeenLastCalledWith('mot [toward]', [
      { start_line: 4, end_line: 4, entry_kind: 'plain', qml_text: 'mot [toward | against]' }
    ]);

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
      rows: [{ start_line: 4, end_line: 4, entry_kind: 'plain', qml_text: 'mot [toward]' }],
      valid_row_count: 1,
      exact_duplicate_count: 0,
      review_rows: [
        {
          start_line: 4,
          end_line: 4,
          entry_kind: 'plain',
          qml_text: 'mot [toward]',
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
              entry_kind: 'plain',
              qml_text: 'mot [against]',
              answer_blocks: ['against']
            }
          ]
        }
      ],
      report_text: '1 row ready',
      committed: false,
      committed_count: 0
    };

    let echoedRows = [{ start_line: 4, end_line: 4, entry_kind: 'plain', qml_text: 'mot [against]' }];
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
    const handleDraftChange = (_qmlText: string, rows: { start_line: number; end_line: number; entry_kind: 'plain' | 'bundle'; qml_text: string }[]): void => {
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
