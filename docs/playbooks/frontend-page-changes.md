# Frontend Page Changes

Use this workflow for page or component work.

1. Keep route components focused on rendering and orchestration.
2. Put shared logic in `frontend/src/lib/**`, named by domain.
3. If a page grows multiple independent sections, split it into subcomponents under `frontend/src/components/<page>/`.
4. Put shared/page styles in `frontend/src/styles/*.css`; leave `frontend/src/app.css` for base/layout styles.
5. Update the matching frontend test file for the page or domain you changed.
6. Run frontend type/build/test checks when the environment allows.
