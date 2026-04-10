Backend service import rule:

- `backend.app.services` is the public backend service surface.
- Service implementation lives under `backend.app.service.*`.
- When adding or removing a public backend service, update `backend/app/services.py`.
- Do not export private helpers from `backend/app/services.py`.

Documentation edit rule:

- Be very thoughtful about adding bloat to `README.md`; keep it short and high-signal.
- Prefer linking to focused docs instead of expanding the main README.
- Other docs are more permissible to edit, but still avoid restating existing information or adding low-signal bulk.
- Avoid root-level convenience files unless they materially enforce behavior; hint-only files are usually not worth the clutter.
