# API: Imports

See also:

- [API index](../api.md)
- [UI imports](../ui/imports.md)
- [Question Markup DSL](../question-markup.md)

Imports are stateless and target one leaf module.

## QML Format

Uploads use one QML entry per plain line or bundle block in `questions.dsl` / QML syntax.

Important behavior:

- one upload targets one leaf module
- repo seed authoring uses `questions.dsl`, and Admin uploads use pasted QML or `.qml` files
- exact duplicate entries are omitted and summarized
- same-leaf duplicate entries can revise the existing question in place
- same-tree prompt matches can move an existing question into a different leaf while keeping question-linked progress
- imported creates and same-tree relocations append at the end of the target leaf while preserving batch order
- deletes and source-module moves leave sparse rank gaps; shared order is append-only
- malformed or conflicting entries are returned for review
- nothing is saved until commit succeeds
- these routes are admin-only

Type inference:

- trailing `{...}` = `multi_text`
- trailing `[...]` with commas = `ordered_multi`
- trailing `[...]` without commas = `single_text`
- embedded `[...]` in the sentence = `inline_cloze`
- top-level `{ ... }` block = `bundle`

## `POST /api/question-imports/validate`

Admin-only.

Validates pasted QML text or an edited entry list.

Request shape:

```json
{
  "module_id": 12,
  "qml_text": "l\u00f8rdag [Saturday]"
}
```

or:

```json
{
  "module_id": 12,
  "rows": [
    { "start_line": 35, "end_line": 35, "entry_kind": "plain", "qml_text": "mot [against|toward]" }
  ]
}
```

Result fields:

- `ready_to_commit`
- `rows`
- `valid_row_count`
- `committable_row_numbers`
- `exact_duplicate_count`
- `review_rows`
- `report_text`
- `committed`
- `committed_count`

Each `review_row` includes:

- `start_line`
- `end_line`
- `entry_kind`
- `qml_text`
- `row_number`
- `qml_line`
- `status`
- `status_text`
- `editable`
- `blocking`
- `target_module_full_slug`
- `current_answer_blocks`
- `imported_answer_blocks`
- `matched_questions`

Review statuses:

- `invalid`
- `duplicate`
- `relocation`
- `info`
- `conflict`

## `POST /api/question-imports/commit`

Admin-only.

Commits the submitted entry list after revalidation.

Commit behavior:

- blocking review entries prevent commit
- exact duplicates commit nothing and report `committed: false`
- successful commits return the same result shape with:
  - `committed: true`
  - `committed_count`
- the frontend uses this endpoint in 50-entry chunks to show determinate save progress
