# QML Generation Prompt

Your job is to transform arbitrary source material into valid QML question lines.

Read the provided material, infer useful study questions from it, and output only final QML.

## Goal

Use this prompt when you want an LLM to:

- read flexible source material
- infer useful study questions from it
- output only valid QML lines
- work entirely within the separate authoring repo

The LLM must not inspect, infer, or reason about any application repo. It should only transform the input it is given into QML output.

## Prompt Template

```text
Convert the provided source material into valid QML question lines.

You are working only on QML generation. Do not inspect, infer, or reason about any application repo or codebase.

Output rules:
- Output only final QML lines.
- Do not output markdown, headings, bullets, comments, JSON, CSV, code, filenames, or explanations.
- Use one question per line.
- You may leave blank lines between questions for readability.
- Do not emit rank or metadata.
- Keep the output suitable for saving directly into one or more `.qml` files.

Source material may be:
- prose notes
- bullet points
- tables
- CSV
- vocabulary lists
- translation pairs
- processed linguistic data
- other structured or semi-structured study material

Transformation rules:
- Infer sensible learner-facing questions from the provided material.
- Preserve meaning while avoiding blind copies of the raw source structure.
- Generate valid QML even when the source is not already written as questions.
- Avoid obvious duplicates within the current output.
- If the source implies bidirectional study questions, generate both directions when useful.
- If the source includes synonyms or accepted variants, include them as `|` alternatives in the same answer slot.

QML rules:
- single_text: Question [answer1 | answer2]
- multi_text unordered: Question {slot1a | slot1b, slot2a | slot2b}
- ordered_multi: Question [slot1a | slot1b, slot2a | slot2b]
- inline_cloze: Sentence with [answer1 | answer2] embedded inline
- Use `|` for alternatives in the same slot.
- Use `,` for separate required slots.
- Use `{}` only for unordered multi-answer questions.
- Use trailing `[]` only for single_text or ordered_multi.
- Use embedded `[]` inside the sentence only for inline_cloze.
- Use `$...$` for inline math, variable bindings, and answer expressions.
- For variable-driven questions, keep expressions small and arithmetic-only.
- Write natural prompt text that a human learner would understand.

Generate only the final QML lines.
```

## Modules And Files

- A module is a topic bucket for related questions.
- Modules may be hierarchical conceptually, but QML generation should target one intended module or topic at a time.
- A module may be authored across one or more `.qml` files.
- The output file name is not fixed by the format; any `.qml` file naming is acceptable.
- Separate `.qml` files may be additive over time.
- Later import into the learning app may ignore duplicate questions, so the authoring repo does not need one single master file.
- Even so, avoid obvious duplicates within the current generated output.

## Supported Question Shapes

### Single Text

One trailing answer box with no slot commas:

```text
What is the capital of Norway? [oslo | christiania]
```

### Multi Text

One trailing unordered answer box:

```text
Name the two rivers that meet at Khartoum. {white nile, blue nile}
```

With alternatives per slot:

```text
Name two rivers in Germany. {rhine | rhein, danube | donau}
```

### Ordered Multi

One trailing ordered answer box:

```text
Name the stages in order. [stage one, stage two, stage three]
```

### Inline Cloze

Answer boxes are embedded directly in the sentence:

```text
The [Amazon | Amazon River] flows through South America.
```

### Variable-Driven Question

Use `$...$` for variable bindings and answer expressions:

```text
Patient needs $m=[1-10]*100$ mg of trycoxigan. The solution has $v=[1-10]*10$ mg/ml. How much solution is needed? [$m/v$ ml]
```

## Flexible Input Example

If the source material is a Norwegian/English CSV or vocabulary table, the LLM should not preserve CSV structure in the output.

Instead, it should generate learner-facing QML such as:

```text
What is the English translation of norsk ord? [english synonym 1 | english synonym 2]
What is the Norwegian translation of english word? [norsk synonym 1 | norsk synonym 2]
```

If the source row supports both directions, generate both directions.

If either language has acceptable synonyms or variants, include them with `|` inside the relevant answer slot.

## Quality Checks

Review generated output for:

- accidental prose outside the QML lines
- malformed bracket or brace structure
- wrong use of `{}` for single-answer questions
- trailing `[]` on inline cloze lines
- undefined variables in answer expressions
- overcomplicated arithmetic in variable-driven questions
- raw CSV or table formatting leaking into the output
