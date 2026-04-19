# Alpha-To-Beta Roadmap

## Summary

Product identity:

- alpha should already be a secure, privately hosted study tool
- beta should be centered on user experience
- experimentation features should come after the core study experience is strong

Key roadmap conclusion:

- the likely beta differentiator is not just polish, but a more performant data model and database design that unlocks faster authoring, richer study modes, portability, and later experimentation

## Alpha Before Beta

### Alpha blockers

- keep the private-hosting auth/session model production-safe
- private hosting with HTTPS and production-safe deployment defaults
- reliable backup/restore for real hosted use
- rank/order performance fixes so imports and bulk authoring are no longer slowed by dense integer-rank updates
- keep a follow-up hardening pass for user-authored text and parsing paths after QML v2 replaces the current math-style surface

### Alpha scope that can continue alongside blockers

- small UX improvements that reduce friction
- content-building tooling improvements

## Beta Release Focus

### Beta pillar 1: Study experience

- complete revise mode
  - full corpus in scope
  - sorted by review value rather than constrained by the normal serving algorithm
  - mastery and very strong items can naturally fall later in the order
- mobile-friendly study modes
  - especially multiple choice
  - authored distractors and prior incorrect answers can both become distractor sources

### Beta pillar 2: Performance and architecture

- redesign the question ordering and database model so the app scales better for:
  - imports
  - bulk edits
  - larger content sets
  - richer future study modes
- use that redesign to support cleaner portability and future experimentation
- avoid keeping dense integer-rank semantics as the long-term core if they continue to dominate write cost

### Beta pillar 3: Authoring and presentation

- QML v2
  - likely move away from inline math-style computed questions toward question bundles
  - bundles would allow curated tested variants instead of inline expression syntax
  - this may imply multiline bundle blocks in QML, or a dedicated bundle section inside QML/import flows
  - exact syntax and storage model are intentionally still undecided
  - bundle direction matters because variants may need to stay logically grouped for study behavior
  - ghost text as lightweight authoring metadata
  - distractors for future multiple-choice support
- theme presets, color schemes, and background patterns
- better import/export UX for the full database

## Later Beta Or Post-Beta

- A/B testing
- alternative repetition algorithms
- derive unseen-question priority from aggregate performance without changing shared catalog order
- polish account-management and authenticated-user UX for private multi-user use
- improve contributor submission visibility, statuses, and review feedback
- continue moderation workflow polish for pending modules, uploaded questions, and revision/delete proposals
- retention comparison across algorithm variants
- bucket-structure changes and scheduler experimentation

These should come after:

- security is solid
- the app is fast enough at scale
- complete revise mode and mobile-friendly study modes are in place

## Assumptions

- alpha is for secure private hosting, not a public-open release
- alpha now includes moderated user contribution flows instead of only single-admin authoring
- beta is study-tool first, not experiment-lab first
- complete revise mode is more important than themes
- QML v2 should follow beta study-mode needs, not lead them
