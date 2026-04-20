Frontend local rules:

- Keep route components focused on rendering and orchestration.
- Put shared non-visual logic in `frontend/src/lib/**`, named by domain.
- Split large page sections into subcomponents under `frontend/src/components/<page>/`.
- Keep shared and page styles in `frontend/src/styles/*.css`; reserve `frontend/src/app.css` for base and layout styles.
- Prefer the current minimalist auth/stats visual direction: restrained headings, sparse graph framing, and minimal support copy.
- Keep import review and edit state in `frontend/src/lib/import-*.ts` and `frontend/src/components/ImportDrawer.svelte`.
- Reuse existing answer-block, prompt-key, and QML-line helpers before adding new parsing or formatting code.
