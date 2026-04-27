import { render, screen } from '@testing-library/svelte';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import ModuleMenu from '../src/components/ModuleMenu.svelte';
import { buildModuleNode } from './builders';

describe('ModuleMenu', () => {
  it('reveals submodules on click, selects parent and child modules, and collapses other top-level branches', async () => {
    const user = userEvent.setup();
    const selectSpy = vi.fn();
    const modules = [
      buildModuleNode({
        id: 1,
        title: 'Biology',
        slug: 'biology',
        full_slug: 'biology',
        children: [
          buildModuleNode({
            id: 2,
            title: 'Plants',
            slug: 'plants',
            full_slug: 'biology/plants',
            instruction: 'Name the plant concept.'
          })
        ]
      }),
      buildModuleNode({
        id: 3,
        title: 'Geography',
        slug: 'geography',
        full_slug: 'geography',
        children: [
          buildModuleNode({
            id: 4,
            title: 'Rivers',
            slug: 'rivers',
            full_slug: 'geography/rivers',
            instruction: 'Name the river system.'
          })
        ]
      })
    ];

    const view = render(ModuleMenu, {
      props: {
        open: true,
        modules,
        selectedModuleId: null,
        selectedModuleLabel: 'Biology',
        onClose: vi.fn(),
        onSelect: selectSpy
      }
    });

    expect(screen.queryByRole('button', { name: 'All Modules' })).toBeNull();
    expect(screen.queryByText('Plants')).toBeNull();

    await user.click(screen.getByRole('button', { name: /Biology biology/i }));
    expect(selectSpy).toHaveBeenCalledWith(1, true);
    expect(screen.getByText('Plants')).toBeTruthy();

    await user.click(screen.getByText('Plants'));
    expect(selectSpy).toHaveBeenCalledWith(2, false);

    await view.rerender({
      open: true,
      modules,
      selectedModuleId: 2,
      selectedModuleLabel: 'Plants',
      onClose: vi.fn(),
      onSelect: selectSpy
    });

    await user.click(screen.getByRole('button', { name: /Geography geography/i }));
    expect(selectSpy).toHaveBeenCalledWith(3, true);

    await view.rerender({
      open: true,
      modules,
      selectedModuleId: 3,
      selectedModuleLabel: 'Geography',
      onClose: vi.fn(),
      onSelect: selectSpy
    });

    expect(screen.queryByText('Plants')).toBeNull();
    expect(screen.getByText('Rivers')).toBeTruthy();
  });
});
