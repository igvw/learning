# bundle

```text
Create bundle blocks for related single-answer question variants.
Output only the final bundle markup. Do not output markdown, headings, bullets, comments, JSON, filenames, or explanations.

Shape:
{Template text with {} placeholders and one trailing []
 {value1} {value2} [answer1 | answer2]
 {value1} {value2} [answer1]}

Rules:
- The whole bundle is wrapped in one top-level { ... } block.
- The first line is the template.
- Use {} in the template for prompt values that change between variants.
- The template must end with exactly one [] answer slot.
- Each following line is one variant row.
- Each row supplies one {...} value for each template placeholder, then one final [...] answer cell.
- Use | for alternative accepted answers in the same answer cell.
- Every prompt value, answer, and alternative should ideally be 1 word.
- Use 2-3 words only for standard, unambiguous phrases.
- Avoid long free-text answers; bundles should vary short parameters and one short answer.

Example:
{A patient needs {} mg of active ingredient. The medication has {} mg/ml of active ingredient. How much medication is needed? []
 {400} {20} [20]
 {500} {30} [16.7 | 16.67]}
```
