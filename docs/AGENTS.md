What belongs here:

- Focused product, API, database, UI, deployment, development, and architecture documentation.

What must not be edited from here:

- Runtime behavior that is not also being implemented and verified.
- Root-level README expansion when a focused doc is the right place.

Local invariants:

- `README.md` stays install-first and short.
- `docs/overview.md` stays conceptual.
- `docs/api.md`, `docs/ui.md`, and `docs/database.md` are factual current-state specs.
- `docs/question-markup.md` and `docs/question-markup-llm-prompt.md` should only be updated together when the actual QML format changes.

Docs update workflow:

- When runtime behavior changes, update the focused doc that owns that behavior:
  - API -> `docs/api.md`
  - UI -> `docs/ui.md`
  - data model -> `docs/database.md`
  - conceptual framing -> `docs/overview.md`
- Keep `README.md` short and install-first.
- Verify changed statements against code or tests before committing them.
- Avoid duplicating the same detailed behavior across multiple docs.
- Remove stale documentation for deprecated or deleted behavior instead of keeping historical guidance in current-state docs.
- Prefer small, meaningful doc edits tied directly to the implemented behavior change.

Preferred extension points:

- Add architecture or process guidance under `docs/architecture.md` when it belongs in the docs tree.
- Update the focused doc that owns the behavior instead of duplicating prose elsewhere.

Common mistakes:

- Repeating the same behavior in overview, UI, and API docs.
- Adding low-signal bulk to `README.md`.
