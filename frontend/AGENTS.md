Frontend design note:

- Prefer the current minimalist auth/stats visual direction for future pages and graphs unless a feature clearly needs something else.
- Keep layouts calm and uncluttered: minimal support copy, fewer nested panels, restrained headings, and clear action rows.
- Prefer simple graph framing over decorative chrome: sparse labels, clean spacing, and accent color used intentionally rather than everywhere.
- When simplifying a surface, remove redundant helper text or duplicate card structure instead of restyling around the clutter.

Frontend change workflow:

- Keep route components focused on rendering and orchestration.
- Put shared logic in `frontend/src/lib/**`, named by domain.
- If a page grows multiple independent sections, split it into subcomponents under `frontend/src/components/<page>/`.
- Put shared and page styles in `frontend/src/styles/*.css`; leave `frontend/src/app.css` for base and layout styles.
- Update the matching frontend test file for the page or domain you changed.
- Run frontend test and build checks when the environment allows.
- When a UI flow or component is superseded, remove the deprecated branch, copy, and dead styling instead of layering new behavior on top.
- If the UI behavior or terminology changes, make the smallest focused update needed in the owning docs.

Import and QML note:

- Keep import review and edit state in `frontend/src/lib/import-*.ts` and `frontend/src/components/ImportDrawer.svelte`.
- Reuse existing answer-block, prompt-key, and QML-line helpers before adding new parsing or formatting code.
