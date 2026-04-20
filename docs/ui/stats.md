# UI: Stats Page

See also:

- [UI index](../ui.md)
- [API study](../api/study.md)
- [Spaced repetition](../spaced-repetition.md)

The stats page combines reporting and question maintenance.

## Main Surface

The page includes:

- recent session performance graph
- spaced-repetition stages graph
- entry-state graph
- retry-eligibility graph
- first-time questions answered by day over the last 7 app-timezone days
- sortable question table
- `Review only` checkbox that filters the same table between non-review and review-flagged rows
- floating create-question action

## Question Table

The table focuses on:

- rank
- prompt
- logical bucket
- last seen
- attempts
- correctness

Table behavior:

- when unchecked, the table shows only non-review rows
- when checked, the table shows only review-flagged rows
- summary cards and graphs stay based on the full module scope while the table is filtered
- unverified uploaded questions and personal revision overlays show badges in the question table
- review rows stay orange when shown in the filtered table
- hot rows are shaded red in two intensities in the main table
- logical bucket and hotness are separated intentionally

## Graph Detail Overlays

- chart layout uses two rows:
  `Latest quiz performance` with `Entry states` on the top row, then `Spaced repetition stages`, `Retry eligibility`, and `First-time questions answered` below
- `Spaced repetition stages` shows the full fixed ladder through `60d`
- clicking `Spaced repetition stages` opens a due-day heatmap overlay
- `Retry eligibility` groups fixed-bucket due times into `<1`, day buckets `1` through `7`, and `>7`
- clicking `Retry eligibility` opens a detail overlay with graph titles plus empty-state or status copy
- the detail overlays keep titles and empty-state or status messaging only; explanatory body copy and count blurbs are omitted
