Backend service import rule:

- `backend.app.services` is the public backend service surface.
- Service implementation lives under `backend.app.service.*`.
- When adding or removing a public backend service, update `backend/app/services.py`.
- Do not export private helpers from `backend/app/services.py`.

Backend Python style rule:

- For backend Python, prefer Python 3.14-native syntax.
- Use built-in generics like `list[...]`, `dict[...]`, and `tuple[...]`.
- Use `T | None` instead of `Optional[T]`, and `A | B` instead of `Union[A, B]`.
- Do not add `from __future__ import annotations` unless there is a specific need.

Documentation edit rule:

- Be very thoughtful about adding bloat to `README.md`; keep it short and high-signal.
- Prefer linking to focused docs instead of expanding the main README.
- Other docs are more permissible to edit, but still avoid restating existing information or adding low-signal bulk.
- Avoid root-level convenience files unless they materially enforce behavior; hint-only files are usually not worth the clutter.
- `docs/question-markup-llm-prompt.md` must remain standalone and copy-pasteable.
- Do not make `docs/question-markup-llm-prompt.md` back-reference other repo docs or tell an external LLM to inspect this repo.
- Keep `docs/question-markup-llm-prompt.md` focused on transforming arbitrary source input into valid QML output.
