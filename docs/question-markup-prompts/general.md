# General

```text
Create study questions in this plain-text markup format.
Output only the final question markup. Do not output markdown, headings, bullets, comments, JSON, filenames, or explanations.
Write one question or one bundle block per entry.
Use natural learner-facing wording.

Answer length:
- Every answer field, blank, alternative, and bundle value should ideally be 1 word.
- Use 2-3 words only for standard, unambiguous phrases.
- Never use long free-text answers; the learner has to type the answer.

Choose the shape:
- Use single answer only when the answer is one word, or rarely a short unambiguous phrase.
- Prefer fill in blanks when sentence context helps make the exact keyword obvious.
- Use unordered multiple answers when several independent answers are required and order should not matter.
- Use ordered multiple answers only for sequences, procedures, rankings, or paths where order matters.
- Use bundles only for closely related variants of the same single-answer pattern.

Fill-in-the-blank quality:
- Each blank needs enough surrounding context that a knowledgeable learner knows what belongs there.
- Do not write vague blanks like [] is the [] of [].
- Prefer sentences where nearby words point clearly to the missing keyword.

Answer syntax:
- Use [answer] for one answer slot.
- Use answer1 | answer2 for alternatives accepted in the same slot.
- Use commas for separate required slots.
- Use {...} at the end for unordered answers where order should not matter.
- Use [...] at the end for a single answer or ordered answers where order matters.
- Use [...] inside the sentence for fill-in-the-blank questions.

Shapes:
Single answer:
What is the capital of Norway? [Oslo]

Unordered multiple answers:
Name two Scandinavian countries. {Norway, Sweden}

Ordered multiple answers:
List the first three planets from the Sun. [Mercury, Venus, Earth]

Fill in blanks:
In cells, the [mitochondrion | mitochondria] produces most ATP.

Bundle of related variants:
{A patient needs {} mg. A solution contains {} mg/ml. How many ml are needed? []
 {400} {20} [20]
 {500} {25} [20]}
```
