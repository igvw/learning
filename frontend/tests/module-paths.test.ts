import { describe, expect, it, vi } from 'vitest';

import { buildModuleNode } from './builders';
import { ensureModulePath } from '../src/lib/module-paths';
import type { ModuleNode } from '../src/lib/types';

describe('module paths', () => {
  it('creates only missing segments for slash-separated module paths', async () => {
    let moduleTree: ModuleNode[] = [
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
            full_slug: 'norwegian/vocabulary'
          })
        ]
      })
    ];

    const createSpy = vi.fn(async ({ title, parent_id: _parentId, instruction }) => {
      const id = title === 'nouns_to_english' ? 3 : 4;
      const fullSlug =
        title === 'nouns_to_english'
          ? 'norwegian/vocabulary/nouns_to_english'
          : 'norwegian/vocabulary/nouns_to_english/plural_forms';
      return buildModuleNode({
        id,
        title,
        slug: title,
        full_slug: fullSlug,
        instruction
      });
    });

    const reloadModules = vi.fn(async () => {
      moduleTree = [
        buildModuleNode({
          ...moduleTree[0],
          children: [
            buildModuleNode({
              ...moduleTree[0].children[0],
              children: [
                buildModuleNode({
                  id: 3,
                  title: 'nouns_to_english',
                  slug: 'nouns_to_english',
                  full_slug: 'norwegian/vocabulary/nouns_to_english',
                  instruction: 'Translate to English.'
                })
              ]
            })
          ]
        })
      ];
      return moduleTree;
    });

    const created = await ensureModulePath({
      modules: moduleTree,
      parentId: null,
      titlePath: 'Norwegian / vocabulary / nouns_to_english',
      instruction: 'Translate to English.',
      createModule: createSpy,
      reloadModules
    });

    expect(createSpy).toHaveBeenCalledTimes(1);
    expect(createSpy).toHaveBeenCalledWith({
      title: 'nouns_to_english',
      parent_id: 2,
      instruction: 'Translate to English.'
    });
    expect(created.full_slug).toBe('norwegian/vocabulary/nouns_to_english');
  });
});
