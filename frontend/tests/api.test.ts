import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { exportContentArchive } from '../src/lib/api';

describe('exportContentArchive', () => {
  const originalCreateObjectUrl = URL.createObjectURL;
  const originalRevokeObjectUrl = URL.revokeObjectURL;

  beforeEach(() => {
    vi.restoreAllMocks();
  });

  afterEach(() => {
    URL.createObjectURL = originalCreateObjectUrl;
    URL.revokeObjectURL = originalRevokeObjectUrl;
    vi.unstubAllGlobals();
  });

  it('downloads the returned zip with the filename from Content-Disposition', async () => {
    const fetchSpy = vi.fn().mockResolvedValue(
      new Response('archive', {
        status: 200,
        headers: {
          'Content-Disposition': 'attachment; filename="modules-export.zip"',
          'Content-Type': 'application/zip'
        }
      })
    );
    vi.stubGlobal('fetch', fetchSpy);

    const createObjectUrlSpy = vi.fn(() => 'blob:modules-export');
    const revokeObjectUrlSpy = vi.fn();
    URL.createObjectURL = createObjectUrlSpy;
    URL.revokeObjectURL = revokeObjectUrlSpy;

    const createdAnchors: HTMLAnchorElement[] = [];
    const originalCreateElement = document.createElement.bind(document);
    vi.spyOn(document, 'createElement').mockImplementation(((tagName: string) => {
      const element = originalCreateElement(tagName);
      if (tagName === 'a') {
        createdAnchors.push(element as HTMLAnchorElement);
      }
      return element;
    }) as typeof document.createElement);
    const clickSpy = vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {});

    await exportContentArchive();

    expect(fetchSpy).toHaveBeenCalledWith('/api/modules/export', { credentials: 'same-origin' });
    expect(createObjectUrlSpy).toHaveBeenCalledTimes(1);
    expect(createdAnchors).toHaveLength(1);
    expect(createdAnchors[0].download).toBe('modules-export.zip');
    expect(clickSpy).toHaveBeenCalledTimes(1);
    expect(revokeObjectUrlSpy).toHaveBeenCalledWith('blob:modules-export');
  });
});
