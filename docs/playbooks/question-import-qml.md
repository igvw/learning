# Import And QML Changes

Use this workflow for question-import and QML-related changes.

1. Keep backend import classification and commit behavior in `backend/app/service/imports.py`.
2. Keep frontend import review/edit state in `frontend/src/lib/import-*.ts` and `frontend/src/components/ImportDrawer.svelte`.
3. Reuse existing answer-block, prompt-key, and QML-line helpers before adding new parsing/formatting code.
4. Update both backend and frontend tests when the import workflow changes.
5. Keep `docs/question-markup.md` and `docs/question-markup-llm-prompt.md` aligned only when the actual format changes.
