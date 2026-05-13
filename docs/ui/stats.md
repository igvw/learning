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
- collapsible question bucket cards
- `Review` checkbox that switches between normal question buckets and pending revision/delete proposals
- floating create-question action

## Question Buckets

Normal bucket cards focus on:

- rank
- prompt
- last seen
- attempts
- correctness

Bucket behavior:

- when `Review` is unchecked, cards show normal quiz-eligible question buckets
- when `Review` is checked, the page shows the `Review` card with pending revision/delete proposals
- pending proposals can be re-edited or removed by the proposing user
- admins can approve, reject, or edit-then-approve pending proposals from the same Review card
- hot rows are shaded red in two intensities in the main table
- clicking `Entry states` opens the all-questions overlay for the active non-review question set

## Graph Detail Overlays

- chart layout uses two rows:
  `Latest quiz performance` with `Entry states` on the top row, then `Spaced repetition stages`, `Retry eligibility`, and `First-time questions answered` below
- `Spaced repetition stages` shows the full fixed ladder through `60d`
- clicking `Spaced repetition stages` opens a due-day heatmap overlay
- `Retry eligibility` groups fixed-bucket due times into `<1`, day buckets `1` through `7`, and `>7`
- clicking `Retry eligibility` opens a detail overlay with graph titles plus empty-state or status copy
- the detail overlays keep titles and empty-state or status messaging only; explanatory body copy and count blurbs are omitted
