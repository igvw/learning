# TODO

This file is the short tracker. The fuller alpha-to-beta product roadmap lives in [roadmap.md](roadmap.md).

## Alpha blockers

- Add private-hosting production safety with HTTPS and security defaults
- Add reliable backup and restore for hosted use
- Fix rank/order performance so imports and bulk authoring scale better
- Keep a follow-up hardening pass for user-authored text and parsing paths after the planned QML rework lands

## Alpha work that can continue in parallel

- Make small UX improvements that reduce friction
- Improve content-building tooling
- Replace the custom schema-version system with `yoyo-migrations` before the next substantial database migration

## Beta focus

- Complete revise mode
- Mobile-friendly study modes, especially multiple choice
- More performant data model and database design
- QML v2, likely moving from computed math syntax toward bundles
- Theme presets and background treatments
- Better full-database import/export UX

## Later beta or post-beta

- A/B testing
- Alternative repetition algorithms
- Derived unseen-question priority based on aggregate performance, kept separate from shared append order
- Polish account-management and authenticated-user UX for private multi-user use
- Improve contributor submission visibility, statuses, and review feedback
- Continue moderation workflow polish for pending modules, uploaded questions, and revision/delete proposals
- Revisit per-user schedule timezones if the app needs to support learners in different regions
- Retention comparisons across variants
- Bucket-structure experimentation
- Persisted or cached schedule state if history-derived scheduling becomes a real scale bottleneck
- Revisit deeper input hardening once QML v2 settles and the math-style surface is gone
