Backend service import rule:

- `backend.app.services` is the public backend service surface.
- Service implementation lives under `backend.app.service.*`.
- When adding or removing a public backend service, update `backend/app/services.py`.
- Do not export private helpers from `backend/app/services.py`.
