Backend change workflow:

- Decide whether a change belongs in the HTTP layer, service layer, or database layer before editing.
- For route-only behavior, edit `backend/app/api/routers/<domain>.py`.
- For backend behavior changes, implement them in `backend/app/service/<domain>.py`.
- If a change adds or removes a public backend capability, update `backend/app/services.py`.
- Prefer cohesive shared helpers in `backend/app/service/errors.py`, `text.py`, `time_utils.py`, or `questions.py` before adding another broad helper module.
- When backend behavior is replaced, remove the deprecated code path, helper, or schema shim unless there is an explicit compatibility requirement.
- If backend behavior changes user-visible or operator-visible semantics, make the smallest focused doc update needed in the owning doc.

Import and QML note:

- Keep import classification and commit behavior in `backend/app/service/imports.py`.
- Reuse existing answer-block, prompt-key, and QML-line helpers before adding new parsing or formatting code.
