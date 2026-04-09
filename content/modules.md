# Content Module Guide

This guide is for agents working only on study content.

Only use these paths:

- `/Users/ignazio/Documents/repos/learning/content/modules`
- `/Users/ignazio/Documents/repos/learning/content/raw`

Do not change app code.

## Directory Layout

Use this structure:

```text
content/
  modules.md
  modules/
    subject/
      module.yaml
      child-topic/
        module.yaml
        questions.dsl
  raw/
    subject/
      child-topic/
        ...
```

Rules:

- every module directory must contain `module.yaml`
- only leaf modules should contain `questions.dsl`
- parent modules group child modules
- `content/raw` is for notes, source material, drafts, and scratch files used to build final QML
- files in `content/raw` are not imported by the app

## `module.yaml`

Each module directory must contain a `module.yaml` file.

Current behavior is intentionally slim:

- only `instruction` matters to the app
- directory structure defines the module path
- module titles are derived from the directory slug

Example:

```yaml
instruction: Translate each Norwegian noun into English.
```

## `questions.dsl`

Each leaf module contains one `questions.dsl` file with one question per line.

Blank lines are allowed and ignored.

Use the current QML syntax from [docs/question-markup.md](../docs/question-markup.md).

Quick reference:

- single answer:
  - `What is the capital of Norway? [oslo]`
- unordered multi-answer:
  - `Name the two rivers that meet in Khartoum. {white nile, blue nile}`
- ordered multi-answer:
  - `Name the stages in order. [stage one, stage two, stage three]`
- inline cloze:
  - `The [Amazon | Amazon River] flows through South America.`
- computed question:
  - `Patient needs $m=[1-10]*100$ mg. Solution strength is $v=[1-10]*10$ mg/ml. How much is needed? [$m/v$ ml]`

Authoring rules:

- keep one logical question per physical line
- use `|` for alternatives in the same slot
- use `{}` for unordered slots
- use `[]` for ordered slots or inline cloze blanks
- keep rank out of the file; import order determines initial rank

## Raw Data Workspace

Use `content/raw` for notes and source material.

Recommended pattern:

```text
content/raw/
  geography/
    rivers/
      notes.md
      source-links.txt
      draft.dsl
```

Nothing in `content/raw` is imported. Final seed content must live in `content/modules`.
