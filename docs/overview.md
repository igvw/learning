# Learning App Overview

This is the main entry point for product documentation.

For system specs, see:

- [API](api.md)
- [UI](ui.md)
- [Database](database.md)

For supporting docs, see:

- [Architecture](architecture.md)
- [Spaced Repetition](spaced-repetition.md)
- [Development](development.md)
- [Deployment](deployment.md)
- [Question Markup DSL](question-markup.md)
- [QML Revised](qml-revised.md)
- [Question Markup Prompts](question-markup-prompts/index.md)
- [TODO](TODO.md)
- [Roadmap](roadmap.md)

## Product

Learning App is a keyboard-first study tool for facts, language, and procedural knowledge. It separates shared content from user-owned progress:

- shared content lives in modules and questions
- shared content can be pending, contributor-owned, or verified
- user progress comes from quiz history
- review flags are user-specific

The stack is:

- FastAPI
- Svelte
- PostgreSQL
- Docker Compose

## Core Concepts

### Modules

Modules form a hierarchy such as `norwegian/vocabulary/nouns_to_english`.

- leaf modules hold questions
- parent modules act as broader study scopes

### Questions

Questions belong to one leaf module and support:

- `single_text`
- `multi_text`
- `ordered_multi`
- `inline_cloze`
- `bundle`

Verified questions are shared. Regular-user revisions and delete requests flow through personal proposals until an admin approves them. `rank` is the authoring and default ordering hint for the shared catalog.

### Users And Progress

The app is multi-user over shared content and authenticated accounts.

- verified modules and questions are shared
- users can own pending uploads and revision proposals
- quiz history is user-owned
- review flags are user-owned
- stats and scheduling are derived per user

### Scheduling

Scheduling uses short-term recovery states, fixed long-term buckets from `1h` through `60d`, and a `mastery` state outside active serving. The serving algorithm is described in [Spaced Repetition](spaced-repetition.md).

### Content And Import

Content can come from repo seed files, admin flows, and moderated user contributions. QML import and question format details live in [API imports](api/imports.md), [UI imports](ui/imports.md), and [Question Markup DSL](question-markup.md).

## Main Surfaces

- [Authentication and account entry](ui/auth.md)
- [Quiz](ui/quiz.md)
- [Stats](ui/stats.md)
- [Manage](ui/manage.md)
- [Imports](ui/imports.md)

## Documentation Principle

This overview stays conceptual. Detailed current-state behavior lives in the focused API, UI, database, deployment, and study docs.
