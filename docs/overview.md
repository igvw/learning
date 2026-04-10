# Learning App Overview

This is the main entry point for the product documentation.

For the current system spec, see:

- [API](api.md)
- [Database](database.md)
- [UI](ui.md)

For supporting docs, see:

- [Spaced Repetition](spaced-repetition.md)
- [Question Markup DSL](question-markup.md)
- [Question Markup LLM Prompt](question-markup-llm-prompt.md)
- [Development](development.md)
- [Deployment](deployment.md)
- [TODO](TODO.md)

## Overview

Learning App is a keyboard-first study tool for facts, language, and procedural knowledge. It separates shared content from user-owned progress:

- shared content lives in modules and questions
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

Questions are edited in place. `rank` is the authoring and default ordering hint.

### Users And Progress

The app is multi-user over shared content.

- users share modules and questions
- quiz history is user-owned
- review flags are user-owned
- stats and scheduling are derived per user

### Scheduling

Scheduling uses:

- short-term hotness states (`hot0`, `hot1`, `hot1_sit_out`)
- fixed long-term buckets (`1h` through `14d`)
- a `mastery` state outside active serving

The serving algorithm is described in [Spaced Repetition](spaced-repetition.md).

### Content And Import

Content can come from repo seed files and from Admin flows.

Current behavior:

- repo seed content still imports from `content/modules`
- modules can be created from the Admin page
- QML imports are stateless and additive
- duplicate prompts in overlapping imports are skipped automatically
- authored question lines live in `questions.dsl`
- the current format is described in [Question Markup DSL](question-markup.md)

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
- spaced-repetition and entry-state graphs
- a sortable question table
- question editing entry points

### Admin

The Admin page owns shared-content administration:

- module creation
- user creation
- question import

## Documentation Principle

This overview stays high-level. The detailed current-state spec lives in [API](api.md), [Database](database.md), and [UI](ui.md), while deployment and study-queue behavior live in focused supporting docs.
