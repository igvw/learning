Backend local rules:

- Route-only behavior lives in `backend/app/api/routers/<domain>.py`.
- Backend domain behavior lives in `backend/app/service/<domain>.py`.
- Public backend capability changes must update `backend/app/services.py`.
- Prefer cohesive shared helpers in `backend/app/service/errors.py`, `text.py`, `time_utils.py`, or `questions.py` before adding another shared module.
- Keep import classification and commit behavior in `backend/app/service/imports.py`.
- Reuse existing answer-block, prompt-key, and QML-line helpers before adding new parsing or formatting code.
