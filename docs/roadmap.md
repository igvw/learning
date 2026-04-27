# Alpha-To-Beta Roadmap

## Summary

The near-term alpha priority is still the authoring transition: finish QML revised, make regular-user question creation smooth without raw QML, and keep admin QML tooling coherent.

Beta should then be built on a cleaner foundation. The biggest beta-scale bet is a redesign of learning-item identity, versioned content, progress state, ordering, and API/type boundaries so the app can scale to larger content sets and richer study modes.

Security hardening, backup automation polish, themes, and experimentation stay on the roadmap, but they are not the active path for the current private self-hosting model.

## Near-Term Alpha

- Land QML revised as explicit top-level `{ ... }` bundle blocks alongside plain one-line QML.
- Redesign the stats-page `Add` flow so regular users can create questions without seeing QML.
- Align the editor, import flow, prompt docs, and review UI around admin-only QML tooling plus structured regular-user authoring.
- Keep contributor/moderation UX polish focused on real friction in the current module, upload, and revision flows.

## Beta Foundation

- Continue splitting the core model into stable learning-item identity, versioned content, variants, and per-user progress state; answered attempts already have a dedicated table.
- Make authoring, import, moderation, and revision proposals one versioned content pipeline instead of parallel mutation paths.
- Treat QML as an import/export syntax that compiles to a normalized internal question model.
- Replace dense integer rank with a more scalable ordering model for imports, moves, and bulk edits.
- Separate module tree identity from displayed path/full-slug concerns.
- Move frontend orchestration toward route/domain loaders or stores, and strengthen API/type contracts between backend and frontend.

## Beta Product UX

- Complete revise mode for the full corpus, ordered by review value rather than the normal serving algorithm.
- Add mobile-friendly study modes, especially multiple choice.
- Improve private multi-user polish around accounts, contribution visibility, review feedback, and admin moderation weight.
- Improve full-database backup/restore UX beyond the documented manual PostgreSQL flow.

## Deferred / Later

- Public-hosting-grade HTTPS/security hardening beyond the current private-hosting defaults.
- Theme presets, color schemes, and presentation polish.
- A/B testing, retention comparisons, alternative repetition algorithms, and bucket/scheduler experiments.
- Derive unseen-question priority from aggregate performance once the app is fast and stable enough at scale.

## Assumptions

- The current hosting model is private self-hosting, not a public-open deployment.
- Alpha includes moderated user contribution flows alongside single-admin authoring.
- Beta is study-tool first, not experiment-lab first.
- Complete revise mode is important, but comes after the immediate QML/add-flow work.
