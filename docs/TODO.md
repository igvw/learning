# TODO

This file is the short tracker. The fuller alpha-to-beta product roadmap lives in [roadmap.md](roadmap.md).

## Alpha blockers

- Finish the authenticated account rollout and moderation UX
- Add private-hosting production safety with HTTPS and security defaults
- Add reliable backup and restore for hosted use
- Fix rank/order performance so imports and bulk authoring scale better
- Keep a follow-up hardening pass for user-authored text and parsing paths after the planned QML rework lands

## Alpha work that can continue in parallel

- Improve the new contribution and moderation workflows
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
- Revisit per-user schedule timezones if the app needs to support learners in different regions
- Retention comparisons across variants
- Bucket-structure experimentation
- Persisted or cached schedule state if history-derived scheduling becomes a real scale bottleneck
- Revisit deeper input hardening once QML v2 settles and the math-style surface is gone
