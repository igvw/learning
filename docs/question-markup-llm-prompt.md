# Question Markup LLM Prompt

This document defines the preferred prompt shape for generating `questions.dsl` content with an LLM.

See also:

- [Question Markup DSL](question-markup.md)

## Goal

Use this prompt when you want an LLM to output valid `questions.dsl` entries directly, without JSON, CSV, or explanatory prose.

## Prompt Template

```text
Generate questions in the Learning App question DSL.

Rules:
- Output only valid DSL question lines.
- Do not output markdown, bullets, JSON, comments, headings, or explanations.
- Use one question per line.
- Leave one blank line between questions if generating multiple questions.
- Do not emit rank.
- Use only the supported line shapes:
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
- For variable questions, keep expressions small and arithmetic-only.
- Write natural prompt text that a human learner would understand.

Generate only the final DSL lines.
```

## Few-Shot Examples

### Single Text

```text
What is the capital of Norway? [oslo | christiania]
```

### Unordered Multi

```text
Name the two rivers that meet at Khartoum. {white nile, blue nile}
```

### Ordered Multi

```text
Name the stages in order. [stage one, stage two, stage three]
```

### Inline Cloze

```text
The [Amazon | Amazon River] flows through South America.
```

### Variable-Driven Question

```text
Patient needs $m=[1-10]*100$ mg of trycoxigan. The solution has $v=[1-10]*10$ mg/ml. How much solution is needed? [$m/v$ ml]
```

## Recommended Constraints For The LLM

When using the prompt in practice, also tell the model:

- the subject area
- the target module instruction
- the number of questions to generate
- whether questions should be simple recall, comprehension, or dosage-style variable questions

Helpful extra constraints:

- keep prompts concise
- avoid duplicate questions
- keep alternatives realistic
- avoid adding capitalization-only variants as alternatives
- for ordered questions, make the sequence genuinely matter
- for inline cloze, keep the sentence readable with one or two blanks

## Quality Checks

Review generated output for:

- accidental prose outside the DSL
- malformed bracket or brace structure
- wrong use of `{}` for single-answer questions
- trailing `[]` on inline cloze lines
- undefined variables in answer expressions
- overcomplicated arithmetic in variable questions

The eventual parser should be treated as the source of truth, but the prompt should aim to reduce invalid generations before parsing.
