# Learning App Overview

This is the main entry point for the product documentation.

For the current system spec, see:

- [API](api.md)
- [Database](database.md)
- [UI](ui.md)

For supporting docs, see:

- [Roadmap](roadmap.md)
- [Architecture](architecture.md)
- [Spaced Repetition](spaced-repetition.md)
- [Question Markup DSL](question-markup.md)
- [Question Markup LLM Prompt](question-markup-llm-prompt.md)
- [Development](development.md)
- [Deployment](deployment.md)
- [TODO](TODO.md)

## Overview

Learning App is a keyboard-first study tool for facts, language, and procedural knowledge. It separates shared content from user-owned progress:

- shared content lives in modules and questions
- shared content can be pending, contributor-owned, or verified
- user progress comes from quiz history
- review flags are user-specific

The current stack is:

- FastAPI
- Svelte
- PostgreSQL
- Docker Compose

## Product Direction

- keep the app simple and fast
- keep content separate from app logic
- support nested modules and multiple users
- make quizzes fast to complete without heavy UI
- make revision and maintenance lightweight
- keep docs human-readable and current

## Core Concepts

### Modules

Modules form a hierarchy such as `norwegian/vocabulary/nouns_to_english`.

- leaf modules hold questions
- parent modules act as broader study scopes
- modules may include an `instruction` so short prompts can stay concise

### Questions

Questions belong to one leaf module and support:

- `single_text`
- `computed_text`
- `multi_text`
- `ordered_multi`
- `inline_cloze`

Verified questions are shared. Regular-user revisions and delete requests now flow through personal proposals until an admin approves them. `rank` remains the authoring and default ordering hint for the shared catalog.

### Users And Progress

The app is multi-user over shared content and authenticated accounts.

- verified modules and questions are shared
- users can also own pending uploads and revision proposals
- quiz history is user-owned
- review flags are user-owned
- stats and scheduling are derived per user

### Scheduling

Scheduling uses:

- short-term recovery states (`hot0`, a one-quiz sit-out, and `hot1`)
- fixed long-term buckets (`1h` through `60d`)
- a `mastery` state outside active serving

The serving algorithm is described in [Spaced Repetition](spaced-repetition.md).

### Content And Import

Content can come from repo seed files, admin flows, and moderated user contributions.

Current behavior:

- repo seed content imports from `content/modules/**/questions.dsl`
- admin and contributor imports use pasted QML or `.qml` files targeted at one leaf module
- exact duplicate import rows are omitted and summarized
- same-leaf duplicate rows can revise the existing question in place
- same-tree prompt matches can move an existing question into a different leaf while keeping its quiz history and derived scheduling
- import-created and import-relocated questions append at the end of the target leaf in batch order
- invalid or conflicting rows stay in review until they are edited or removed
- leaf modules can be renamed from Admin without changing the underlying module id
- the current question-line format is described in [Question Markup DSL](question-markup.md)

## Main Screens

### Quiz

The quiz page is the active recall surface.

- one active unanswered card at a time
- answered cards remain on screen
- `Enter` advances and submits
- correct and incorrect answers get immediate color feedback
- the completed session becomes the review surface

### Stats

The stats page combines:

- recent quiz performance
- entry-state, spaced-repetition, retry-eligibility, and first-time-answered graphs
- a sortable question table filtered between non-review and review-only rows
- question revision and delete entry points

### Admin

The third route is now role-aware:

- admins get account management, shared-content management, and moderation queues
- regular users get pending module/question authoring plus a view of their own submissions
- demo shows the same contribution affordances in a non-persistent showcase mode

## Documentation Principle

This overview stays high-level. The detailed current-state spec lives in [API](api.md), [Database](database.md), and [UI](ui.md), while deployment and study-queue behavior live in focused supporting docs.
