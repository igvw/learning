# single_text

```text
Create study questions with one required answer.
Output only the final question markup. Do not output markdown, headings, bullets, comments, JSON, filenames, or explanations.

Shape:
Prompt [answer1 | answer2]

Rules:
- Put one answer slot at the end in square brackets.
- Use | for alternative accepted answers in the same slot.
- Do not use commas inside the brackets unless the comma is part of the answer text.
- The answer should ideally be 1 word.
- Use 2-3 words only for a standard, unambiguous phrase.
- Avoid long free-text answers; rephrase or use a fill-in-the-blank sentence instead.

Examples:
What is the capital of Norway? [Oslo]
What gas do plants absorb during photosynthesis? [carbon dioxide | CO2]
```
