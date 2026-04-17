What belongs here:

- Focused product, API, database, UI, deployment, development, and architecture documentation.

What must not be edited from here:

- Runtime behavior that is not also being implemented and verified.
- Root-level README expansion when a focused doc is the right place.

Local invariants:

- `README.md` stays install-first and short.
- `docs/overview.md` stays conceptual.
- `docs/api.md`, `docs/ui.md`, and `docs/database.md` are factual current-state specs.
- Playbooks should describe editing workflows, not restate product behavior.

Preferred extension points:

- Add architecture/process guidance under `docs/architecture.md` or `docs/playbooks/`.
- Update the focused doc that owns the behavior instead of duplicating prose elsewhere.

Common mistakes:

- Repeating the same behavior in overview, UI, and API docs.
- Turning playbooks into general product docs.
- Adding low-signal bulk to `README.md`.
