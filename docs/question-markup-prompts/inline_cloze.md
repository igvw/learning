# inline_cloze

```text
Create fill-in-the-blank study questions where answers appear inside the sentence.
Output only the final question markup. Do not output markdown, headings, bullets, comments, JSON, filenames, or explanations.

Shape:
Sentence with [answer1 | answer2] embedded inline.

Rules:
- Put answer slots inside the sentence in square brackets.
- Use one bracket group per blank.
- Use | for alternative accepted answers in the same blank.
- Do not add a separate answer list at the end.
- Each blank or alternative should ideally be 1 word.
- Use 2-3 words only for a standard, unambiguous phrase.
- Give enough surrounding context that a knowledgeable learner knows what belongs in each blank.
- Do not write vague blanks like [] is the [] of [].

Examples:
In cells, the [mitochondrion | mitochondria] produces most ATP.
Water freezes at [0] degrees Celsius.
```
