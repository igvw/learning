# multi_text

```text
Create study questions with multiple required answers where order should not matter.
Output only the final question markup. Do not output markdown, headings, bullets, comments, JSON, filenames, or explanations.

Shape:
Prompt {slot1a | slot1b, slot2a | slot2b}

Rules:
- Put all required answer slots at the end in curly braces.
- Separate required slots with commas.
- Use | for alternative accepted answers in the same slot.
- Order should not matter.
- Each answer slot or alternative should ideally be 1 word.
- Use 2-3 words only for standard, unambiguous phrases.
- Avoid long free-text answers.

Examples:
Name two Scandinavian countries. {Norway, Sweden}
Name two noble gases. {helium | He, neon | Ne}
```
