# Backend Service Changes

Use this workflow for backend behavior changes.

1. Decide whether the change is HTTP-layer, service-layer, or database-layer.
2. If it is HTTP-only, edit `backend/app/api/routers/<domain>.py`.
3. If it changes behavior, implement it in `backend/app/service/<domain>.py`.
4. If the change adds or removes a public backend capability, update `backend/app/services.py`.
5. Prefer cohesive shared helpers in `backend/app/service/errors.py`, `text.py`, `time_utils.py`, or `questions.py` instead of adding another broad helper file.
6. Add or update backend tests in the matching domain suite.
7. Run backend checks and the backend unittest suite.
