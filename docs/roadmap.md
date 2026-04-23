# Alpha-To-Beta Roadmap

## Summary

Product identity:

- alpha should already be a secure, privately hosted study tool
- beta should be centered on user experience
- experimentation features should come after the core study experience is strong

Key roadmap conclusion:

- the immediate next product step is the authoring transition: explicit QML revised top-level bundle blocks and a smooth non-QML add flow for regular users
- the likely beta differentiator after that is still a more performant data model and database design that unlocks faster authoring, richer study modes, portability, and later experimentation

## Near-Term Focus

- land QML revised as explicit top-level `{ ... }` bundle blocks while keeping plain one-line QML for non-bundle questions
- make the stats-page `Add` flow smooth for regular users now that QML is admin-only
- keep admin QML tooling available while the structured regular-user authoring flow catches up

## Deferred Or Lower-Priority Alpha Work

- keep the private-hosting auth/session model production-safe
- keep private-hosting deployment defaults strong enough for self-hosted use
- keep a follow-up hardening pass for user-authored text and parsing paths after QML revised settles
- future backup/restore work is automation and polish, not basic capability, because a manual PostgreSQL migration and backup path is already documented

## Beta Release Focus

### Beta pillar 1: Study experience

- complete the authoring transition before deeper study-mode expansion
  - QML revised bundles should be stable enough that regular-user creation does not depend on raw QML
- complete revise mode
  - full corpus in scope
  - sorted by review value rather than constrained by the normal serving algorithm
  - mastery and very strong items can naturally fall later in the order
- mobile-friendly study modes
  - especially multiple choice
  - better distractor sourcing can come later, for example from prior incorrect answers

### Beta pillar 2: Performance and architecture

- redesign the question ordering and database model so the app scales better for:
  - imports
  - bulk edits
  - larger content sets
  - richer future study modes
- keep this below the near-term QML/add-flow work even though it remains strategically important
- use that redesign to support cleaner portability and future experimentation
- avoid keeping dense integer-rank semantics as the long-term core if they continue to dominate write cost

### Beta pillar 3: Authoring and presentation

- QML revised
  - use explicit top-level `{ ... }` bundle blocks alongside plain one-line QML
  - bundles should stay one learning item with shared history while each quiz serving resolves one concrete variant
  - first implementation priority is import/export, storage, and runtime before regular-user authoring UI
  - see [QML Revised](qml-revised.md) for the current design/planning direction
- regular-user question creation should become structured and non-QML-first
- theme presets, color schemes, and background patterns
- better automated backup/restore and import/export UX for the full database

## Later Beta Or Post-Beta

- A/B testing
- alternative repetition algorithms
- derive unseen-question priority from aggregate performance without changing shared catalog order
- polish account-management and authenticated-user UX for private multi-user use
- improve the remaining contributor submission visibility, statuses, and review feedback gaps
- continue moderation workflow polish where the current module/upload/revision overlays still feel heavy
- retention comparison across algorithm variants
- bucket-structure changes and scheduler experimentation

These should come after:

- the QML/authoring transition is stable
- the app is fast enough at scale
- complete revise mode and mobile-friendly study modes are in place

## Assumptions

- the current hosting model is private self-hosting, not a public-open deployment
- alpha includes moderated user contribution flows alongside single-admin authoring
- beta is study-tool first, not experiment-lab first
- the next high-value step is the authoring transition, not public-hosting hardening
- complete revise mode is more important than themes, but comes after the immediate QML/add-flow work
