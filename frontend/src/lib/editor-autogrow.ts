export type AutoGrowParams = { maxMode?: 'compact' | 'wide'; value?: string };

export function autoGrow(
  node: HTMLTextAreaElement,
  params: AutoGrowParams = {}
): { update: (next?: AutoGrowParams) => void; destroy: () => void } {
  let options = params;
  const mirror = document.createElement('div');
  mirror.style.position = 'absolute';
  mirror.style.visibility = 'hidden';
  mirror.style.pointerEvents = 'none';
  mirror.style.whiteSpace = 'pre';
  mirror.style.left = '-9999px';
  mirror.style.top = '0';
  document.body.appendChild(mirror);

  const resize = () => {
    const style = window.getComputedStyle(node);
    mirror.style.font = style.font;
    mirror.style.fontKerning = style.fontKerning;
    mirror.style.letterSpacing = style.letterSpacing;
    mirror.style.textTransform = style.textTransform;

    const panelWidth = node.closest('.drawer-panel')?.clientWidth ?? node.parentElement?.clientWidth ?? 720;
    const maxWidth =
      options.maxMode === 'wide'
        ? Math.max(320, panelWidth - 96)
        : Math.max(240, Math.floor((panelWidth - 96) / 3));
    const minWidth = Math.min(maxWidth, 240);
    const content = node.value
      .split('\n')
      .reduce((longest, line) => (line.length > longest.length ? line : longest), ' ');
    mirror.textContent = content || ' ';
    const measuredWidth = Math.max(
      minWidth,
      Math.min(maxWidth, Math.ceil(mirror.getBoundingClientRect().width) + 26)
    );
    node.style.width = `${measuredWidth}px`;
    node.style.height = '0px';
    const singleLineHeight =
      (Number.parseFloat(style.lineHeight) || 22) +
      (Number.parseFloat(style.paddingTop) || 0) +
      (Number.parseFloat(style.paddingBottom) || 0) +
      (Number.parseFloat(style.borderTopWidth) || 0) +
      (Number.parseFloat(style.borderBottomWidth) || 0);
    node.style.height = `${Math.max(singleLineHeight, node.scrollHeight)}px`;
  };

  const resizeObserver = typeof ResizeObserver === 'undefined' ? null : new ResizeObserver(resize);
  if (resizeObserver && node.parentElement) {
    resizeObserver.observe(node.parentElement);
  }
  node.addEventListener('input', resize);
  queueMicrotask(resize);

  return {
    update(next: AutoGrowParams = {}) {
      options = next;
      resize();
    },
    destroy() {
      resizeObserver?.disconnect();
      node.removeEventListener('input', resize);
      mirror.remove();
    }
  };
}
