# Content Module Guide

This guide is for an agent working only on learning content.

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
        questions.csv
  raw/
    subject/
      child-topic/
        ...
```

Rules:

- Every module directory must contain `module.yaml`.
- Only leaf modules should contain `questions.csv`.
- Parent modules group child modules.
- `content/raw` is for notes, source material, drafts, and scratch files used to build `questions.csv`.
- Files in `content/raw` are not imported by the app.

## `module.yaml`

Each module directory must contain a `module.yaml` file.

Top-level module example:

```yaml
source_id: geography
title: Geography
ui_copy:
  question_label: Prompt
  answer_label: Accepted answer
  stats_title: Geography Stats
  review_title: Geography Review
```

Child module example:

```yaml
source_id: geography-rivers
title: Rivers
parent_source_id: geography
ui_copy:
  question_label: River prompt
  answer_label: River answer
  stats_title: River Stats
  review_title: River Review
```

Fields:

- `source_id`: required, unique, stable
- `title`: required
- `parent_source_id`: required for child modules, omitted for top-level modules
- `ui_copy`: optional

`source_id` guidance:

- Use short ASCII ids.
- Prefer names like `subject-topic`.
- Never rename an existing `source_id`.

## `questions.csv`

Each leaf module must contain one `questions.csv` file with this exact header:

```csv
source_id,module_source_id,type,ranking,prompt,accepted_answers_json,slot_prompts_json,segments_json
```

Column meanings:

- `source_id`: required, unique, stable
- `module_source_id`: required, must match the leaf module `source_id`
- `type`: `single_text`, `multi_text`, `ordered_multi`, or `inline_cloze`
- `ranking`: numeric importance, usually `1` to `5`
- `prompt`: short question text
- `accepted_answers_json`: JSON array of accepted answer groups
- `slot_prompts_json`: keep this column in the file, but usually leave it empty
- `segments_json`: only used by `inline_cloze`

`source_id` guidance:

- Prefer names like `subject-topic-001`
- Example: `geography-rivers-003`
- Never reuse an old `source_id` for a different question

## Question Types

### `single_text`

One input box.

Rules:

- `accepted_answers_json` must have exactly one answer group
- `slot_prompts_json` must be empty
- `segments_json` must be empty

Example:

```csv
geography-rivers-001,geography-rivers,single_text,5,Which river runs through Cairo?,"[[""nile"",""the nile""]]","",""
```

### `multi_text`

Multiple input boxes. Answer order does not matter.

Rules:

- `accepted_answers_json` must have one answer group per required answer
- `slot_prompts_json` should be empty
- `segments_json` must be empty

Example:

```csv
geography-rivers-002,geography-rivers,multi_text,4,Name the two rivers that meet in Khartoum.,"[[""white nile""],[""blue nile""]]","",""
```

### `ordered_multi`

Multiple input boxes. Answer order does matter.

Rules:

- Same CSV shape as `multi_text`
- Use only when the sequence itself is important

Example use cases:

- ordered steps
- ranked lists
- first/second/third answers

### `inline_cloze`

Inline blanks rendered inside text.

Rules:

- `accepted_answers_json` must have one answer group per blank
- `slot_prompts_json` must be empty
- `segments_json` must contain exactly one more segment than answer groups

Example:

```csv
geography-rivers-003,geography-rivers,inline_cloze,3,Amazon basin sentence,"[[""amazon"",""amazon river""]]","","[""The "","" flows mainly through South America.""]"
```

For `inline_cloze`, the prompt is still useful as a short label for tables and editing. The actual inline blanks come from `segments_json`, and the app renders them with `[_]` between the segments.

## `accepted_answers_json`

This is always a JSON array of answer groups.

Example:

```json
[["primary answer", "alternate answer"], ["second required answer"]]
```

Meaning:

- Each outer array item is one required answer slot or blank.
- Each inner array item is an accepted synonym for that slot.

Authoring rules:

- Put the preferred display answer first in each group.
- Add only real synonyms.
- Do not add capitalization-only variants.
- Use `multi_text` for unordered answers.
- Use `ordered_multi` only when order is required.

## Raw Data Workspace

Use `content/raw` for the material you use to build the final CSV.

Recommended pattern:

```text
content/raw/
  geography/
    rivers/
      notes.md
      source-links.txt
      draft.csv
```

Nothing in `content/raw` is imported. Final seed content must live in `content/modules`.
