# Question Markup DSL

This document defines the first version of `questions.dsl`, a human-readable plain-text format for authoring question content.

The goal is to replace CSV conceptually without inheriting CSV's separator problems. The format is designed to be:

- readable in a normal text editor
- easy to diff in git
- predictable for LLM generation
- close to the app's existing question model

This is the current authoring and seed-content format used by the app.

See also:

- [Overview](overview.md)
- [API](api.md)
- [TODO](TODO.md)
- [QML Revised](qml-revised.md)
- [QML Prompt Snippets](question-markup-prompts/index.md)

## File Shape

- one leaf module gets one `questions.dsl` file
- one question entry lives on one logical line
- entries may be separated by blank lines for readability
- `rank` is not written in the DSL
- import assigns append order by insertion order
- manual admin export writes a zip rooted at `modules-export/content/modules/`, with `module.yaml` in every verified module and `questions.qml` in every verified leaf

## Cheat Sheet

- `|` separates alternatives for the same answer slot
- `,` separates required slots
- `{...}` means unordered slots
- `[...]` at the end of a line means either:
  - one single-answer slot, or
  - an ordered list of slots if commas are present
- `[...]` inside the question text means inline cloze blanks
- `$...$` means inline math or a variable binding / answer expression
- backslash escapes reserved literal characters

## Four Question Shapes

### Single Text

One trailing answer box with no slot commas:

```text
What is the capital of Norway? [oslo | christiania]
```

Meaning:

- `question_type = single_text`
- one answer group
- alternatives inside the same slot are separated by `|`

### Multi Text

One trailing unordered answer box:

```text
Name the two rivers that meet at Khartoum. {white nile, blue nile}
```

With alternatives per slot:

```text
Name two rivers in Germany. {rhine | rhein, danube | donau}
```

Meaning:

- `question_type = multi_text`
- one required slot per comma
- slot order does not matter

### Ordered Multi

One trailing ordered answer box:

```text
Name the stages in order. [stage one, stage two, stage three]
```

With alternatives per slot:

```text
Name the stages in order. [stage one | first stage, stage two | second stage]
```

Meaning:

- `question_type = ordered_multi`
- one required slot per comma
- slot order does matter

### Inline Cloze

Answer boxes are embedded directly in the sentence:

```text
The [Amazon | Amazon River] flows through South America.
```

Multiple blanks:

```text
The [heart] pumps [blood] through the body.
```

Meaning:

- `question_type = inline_cloze`
- each embedded bracket group becomes one blank
- alternatives inside a blank are separated by `|`
- there is no separate trailing answer box

## Type Inference

The DSL deliberately uses a few easy-to-distinguish shapes.

Infer type using these rules:

- trailing `{...}` means `multi_text`
- trailing `[...]` with commas means `ordered_multi`
- trailing `[...]` without commas means `single_text`
- `[...]` embedded inside the sentence before line end means `inline_cloze`

Practical interpretation:

- `What is the capital of Norway? [oslo]` is `single_text`
- `Name the stages in order. [stage one, stage two]` is `ordered_multi`
- `The [Amazon] flows through South America.` is `inline_cloze`

## Mapping To The Current App Model

The future parser/import path should compile DSL lines into the current internal shape:

- `question_type`
- `accepted_answers`
- `segments`
- synthesized `rank`

### `accepted_answers`

Each required slot becomes one answer group.

Examples:

```text
What is the capital of Norway? [oslo | christiania]
```

becomes conceptually:

```json
[["oslo", "christiania"]]
```

```text
Name two rivers in Germany. {rhine | rhein, danube | donau}
```

becomes conceptually:

```json
[["rhine", "rhein"], ["danube", "donau"]]
```

### `segments`

Only `inline_cloze` uses `segments`.

Example:

```text
The [Amazon | Amazon River] flows through South America.
```

becomes conceptually:

```json
{
  "accepted_answers": [["Amazon", "Amazon River"]],
  "segments": ["The ", " flows through South America."]
}
```

### `rank`

`rank` is intentionally omitted from authoring.

Current import behavior:

- append questions in upload order
- keep question order server-managed rather than editor-controlled

## Math And Variables

Use `$...$` for:

- ordinary inline math
- variable bindings
- answer expressions

### Inline Math

Example:

```text
What does $H_2O$ represent? [water]
```

### Variable Bindings

A variable binding is recognized by assignment inside `$...$`.

Examples:

```text
$m=[1-10]*100$
$v=[1-10]*10$
```

These bindings live inline on the question side.

### Variable-Driven Questions

Example:

```text
Patient needs $m=[1-10]*100$ mg of trycoxigan. The solution has $v=[1-10]*10$ mg/ml. How much solution is needed? [$m/v$ ml]
```

Meaning:

- the prompt samples concrete values for `m` and `v`
- the answer box uses those sampled values in an expression
- the learner is checked against the rendered final answer text, not the formula itself

### V1 Expression Scope

Keep the first version small:

- small arithmetic only
- variable bindings like `$m=[1-10]*100$`
- answer expressions like `$m/v$`
- no large symbolic math language

## Escaping

Use backslashes for literal reserved characters:

- `\|`
- `\,`
- `\{`
- `\}`
- `\[`
- `\]`
- `\$`
- `\\`

Examples:

```text
What symbol is used for "or"? [\|]
```

```text
Which punctuation mark appears here: "$"? [\$]
```

## Valid And Invalid Patterns

### Valid

```text
What is the capital of Norway? [oslo | christiania]
```

```text
Name the two rivers that meet at Khartoum. {white nile, blue nile}
```

```text
Name the stages in order. [stage one, stage two, stage three]
```

```text
The [Amazon | Amazon River] flows through South America.
```

```text
Patient needs $m=[1-10]*100$ mg. The solution has $v=[1-10]*10$ mg/ml. How much is needed? [$m/v$ ml]
```

### Invalid

```text
What is the capital of Norway? {oslo}
```

Reason: trailing `{...}` means unordered multi, not single-answer.

```text
The [Amazon flows through South America.
```

Reason: unbalanced brackets.

```text
Name the stages in order. [stage one | first stage,]
```

Reason: malformed ordered slot list.

```text
Patient needs $m=[1-10]*100$ mg. How much is needed? [$m/z$ ml]
```

Reason: `z` is unbound.

## Bundle Blocks

This document describes the current QML/DSL format only.

Top-level `{ ... }` bundle blocks are documented separately in [QML Revised](qml-revised.md).
