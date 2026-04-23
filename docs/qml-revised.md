# QML Revised

This document is the design home for the next authoring format direction.

It does **not** describe the current format that ships today. For current behavior, see [Question Markup DSL](question-markup.md).

## Summary

QML revised keeps the current plain one-line QML format for ordinary non-bundle questions, while adding explicit top-level `{ ... }` blocks for grouped variants.

The key direction is:

- plain one-line QML stays valid for `single_text`, `multi_text`, `ordered_multi`, and `inline_cloze`
- bundles are first-class authoring/runtime units, not just import sugar
- one bundle maps to one learning item with shared progress/history
- each quiz serving resolves one concrete variant before the quiz item is persisted
- numeric acceptance stays explicit for now; built-in rounding/tolerance semantics are deferred

## Why This Exists

The current line-based QML format works well for:

- simple text questions
- admin import
- diffable seed content
- lightweight LLM generation

But it is not the desired long-term authoring model for:

- grouped variants that should stay logically tied together
- structured regular-user creation flows
- explicit parameterized variants that stay bundled together

The app is still alpha, so this document uses the label **QML revised** instead of pretending there is already a stable versioned format contract to preserve.

## Locked Decisions

- the future format direction is called **QML revised**
- bundles use **explicit block syntax**, not implicit continuation and not YAML
- bundles are **first-class runtime/storage concepts**
- plain one-line QML remains valid alongside bundles
- v1 bundle scope is intentionally **single-answer only**
- ghost text and distractors are explicitly out of scope for this first bundle design

## File Model

A `questions.qml` file may contain:

- plain current-style one-line questions
- top-level `{ ... }` bundle blocks

Plain lines remain valid for `single_text`, `multi_text`, `ordered_multi`, and `inline_cloze`.

Blank lines may appear between questions and between bundle rows for readability. Nested bundle blocks are not part of the design.

## Bundle Syntax

Recommended surface:

```text
{A patient needs {} mg of active ingredient. The medication has {} mg/ml of active ingredient. How much medication does the patient need? []
 {400} {20} [20]
 {600} {30} [20]
 {500} {30} [16.7 | 16.67]}
```

## Template Rules

- the first non-blank line inside a bundle is the template line
- the template line must resolve to a single-answer question
- `{}` marks a prompt-value placeholder
- `[]` marks the single answer slot
- placeholders are positional and anonymous in v1
- the number of `{}` prompt placeholders defines how many prompt-value cells each variant row must provide

### Placeholder Kinds

There are two placeholder kinds:

- prompt-text placeholder: contributes literal text into the rendered prompt
- answer-group placeholder: contributes one accepted-answer group

In v1, bundle templates support only one answer-group placeholder: the trailing `[]` slot.

An answer-group placeholder stands for the entire slot, not part of a slot.

## Variant Row Rules

- each variant row starts with `-`
- each row supplies one cell for each distinct placeholder number, in numeric order
- cell kinds are explicit:
  - `{...}` = prompt-text cell
  - `[...]` = accepted-answer-group cell
- the template decides which kind each position expects
- a variant row must match the template’s expected cell count and cell kinds exactly
- answer alternatives inside `[...]` keep current `|` behavior

Examples:

- template `{{1}} ... {{2}} ... [{{3}}]` expects:
  - `{...} {...} [...]`
- template `The [{{1}}] pumps [{{2}}].` expects:
  - `[...] [...]`
- template `Name two rivers. { {{1}}, {{2}} }` expects:
  - `[...] [...]`

Numeric acceptance such as `[16.7 | 16.67]` stays explicit in the row for now. QML revised does not add built-in rounding or tolerance rules in this first design.

## Runtime Meaning

A bundle is one learning item:

- one question identity
- one scheduling/progress history
- one review-flag target
- one moderation/revision target

When a quiz item is created:

- the app picks one bundle variant uniformly at random
- that variant resolves into the existing serving shape plus accepted answers
- the resolved prompt and resolved answer config are persisted into `quiz_session_items`

After that resolution step, quiz UI, answer checking, stats, and feedback should continue to operate on the existing resolved model.

This keeps learner-facing APIs shape-based while still giving bundles shared identity underneath.

## Storage And Identity

The storage direction should keep `questions` as the stable learner-facing identity.

Recommended model:

- `questions` remains the main learning-item table and scheduling/progress key
- `questions.question_type` continues to store the resolved serving shape, not a new bundle-only type
- bundle-backed questions get a 1:1 bundle record
- each bundle stores an ordered list of variants as child rows
- bundle metadata stores enough normalized structure to support:
  - import validation
  - export round-tripping
  - duplicate detection
  - revision/moderation diffing later

The exact table and JSON field names can be chosen during implementation, but the architecture should not flatten bundles back into unrelated question rows.

## Import, Export, And Prompt Identity

Import/export should become bundle-aware:

- plain non-bundle questions still round-trip as one line each
- bundle-backed questions export back out as `bundle { ... }` blocks
- variant order is preserved

Prompt identity should follow the template skeleton, not a single resolved variant. That matters for:

- duplicate detection
- same-tree relocation logic
- future revision matching

In practice, this means bundle identity should be keyed from the normalized template structure plus serving shape, not from one sampled prompt.

## Rollout Order

### Phase 1: Import, export, storage, runtime

- add bundle parsing and validation
- add bundle export formatting
- add first-class bundle storage
- resolve bundle variants at quiz-session creation
- persist the resolved prompt/type-config into `quiz_session_items`
- keep the supported authoring syntax focused on plain one-line questions plus bundle blocks

This phase should not yet redesign the regular-user add flow.

### Phase 2: Admin authoring and review

- make the admin editor bundle-aware
- make import review bundle-aware
- make moderation and revision review bundle-aware
- allow admins to inspect bundle-backed questions without flattening them mentally into unrelated rows

### Phase 3: Structured regular-user authoring

- build the stats-page `Add` flow around the bundle model rather than raw QML
- keep raw QML as the advanced/admin path
- move regular-user question creation toward structured forms instead of line editing

## Out Of Scope For This First Design

- built-in rounding or tolerance semantics
- ghost text
- distractors
- weighted variant selection
- final table/field names
- the exact structured UI for regular-user creation

## Open Details Still Intentionally Undecided

- the exact normalized storage schema for bundle templates and cells
- the exact prompt-key normalization algorithm for bundles
- whether export preserves some original formatting or always canonicalizes bundle layout
- whether plain one-line QML remains a permanent subset or becomes mostly admin shorthand later

## Likely Future Impact Areas

When implementation starts, this direction is likely to affect:

- `question_type`
- import parsing and validation
- export generation
- quiz-session creation
- editor/add flows
- moderation/revision review
- runtime/storage representation
