# QML Revised

This document describes the implemented bundle direction for QML revised. The plain-line syntax is still documented separately in [Question Markup DSL](question-markup.md).

## Summary

QML revised keeps plain one-line QML for simple questions and adds top-level `{ ... }` bundle blocks for grouped single-answer variants.

The current model is:

- plain one-line QML remains valid for `single_text`, `multi_text`, `ordered_multi`, and `inline_cloze`
- bundle blocks create `question_type = "bundle"` questions
- one bundle is one learning item with shared progress, review flags, revisions, and scheduling
- each quiz serving resolves one concrete bundle variant before the quiz item is persisted
- accepted numeric forms are written explicitly as answer alternatives; built-in rounding/tolerance is not part of the format

## Why This Exists

Plain QML works well for compact seed content, admin import, and lightweight LLM generation. Bundles cover a different need: several closely related variants that should be authored, reviewed, exported, and scheduled as one learning item instead of as unrelated rows.

The app is still alpha, so **QML revised** is a direction label rather than a compatibility-version contract.

## File Model

A `questions.qml` file may contain:

- plain current-style one-line questions
- top-level `{ ... }` bundle blocks

Blank lines may appear between entries. Nested bundle blocks are not supported.

## Bundle Syntax

Canonical bundle blocks use a template line followed by one variant row per line:

```text
{A patient needs {} mg of active ingredient. The medication has {} mg/ml of active ingredient. How much medication does the patient need? []
 {400} {20} [20]
 {600} {30} [20]
 {500} {30} [16.7 | 16.67]}
```

The closing `}` may appear on the same line as the final variant row.

## Template Rules

- the first non-blank line inside the block is the template line
- `{}` marks a prompt-value placeholder
- `[]` marks the single answer slot
- placeholders are positional and anonymous
- v1 bundles support one answer slot
- the number of `{}` placeholders determines how many prompt cells every variant row must provide

## Variant Row Rules

- each variant row supplies prompt cells followed by one answer cell
- `{...}` supplies one prompt substitution value
- `[...]` supplies the accepted answers for the answer slot
- row cell count and cell kinds must match the template exactly
- answer alternatives inside `[...]` keep the normal `|` behavior

For example, this template:

```text
{} has a dose of {} mg. What is the total? []
```

expects rows shaped like:

```text
{Paracetamol} {500} [500 mg | 500]
```

## Storage And Runtime

Bundles are first-class question content, not import-only sugar:

- `questions` remains the stable learning-item table and progress key
- `questions.question_type` is `"bundle"` for bundle-backed questions
- `questions.prompt` stores the canonical template line
- `questions.prompt_key` is based on the normalized template identity
- `questions.type_config_json` stores lightweight bundle summary metadata
- `question_bundles` stores one row per bundle variant
- `question_bundles.variant_index` preserves authoring/export order
- each variant row stores `prompt_values_json` and `accepted_answers_json`

When a quiz session is created, the runtime picks one variant uniformly at random, stores that variant id on the session item, substitutes prompt values into the template, and persists the resolved prompt plus accepted answers for the active quiz UI. Once answered, the durable attempt points to the exact question version and bundle variant that was served.

## Import, Export, And Review

- import parsing is entry-based: one entry is either a plain line or a bundle block
- plain questions export as one line each
- bundle questions export as canonical `{ ... }` blocks
- import review, editor, moderation, and revision UI treat bundles as their own section rather than flattening variants into independent plain questions
- bundle revision proposals store a full proposed bundle snapshot so admin review can compare the whole bundle

## Deferred Ideas

These are intentionally outside the current bundle model:

- built-in rounding or tolerance semantics
- ghost text
- distractors
- weighted variant selection
- multi-answer or inline-cloze bundle variants
- a more normalized SQL model for individual answer cells
