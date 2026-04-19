# Spaced Repetition

The scheduler has two layers:

- hot recovery for recently missed questions
- fixed review buckets for longer-term spacing

## Serving Priority

1. `hot0`
2. `hot1`
3. due fixed-bucket questions, shortest bucket first
4. unseen questions

Review-flagged questions are skipped. `mastery` questions are not served.

## States

- `unseen`
- `hot0`: wrong and immediately eligible again
- `hot1`: right after `hot0`, but only after sitting out one full quiz
- fixed buckets: `1h`, `3h`, `6h`, `12h`, `1d`, `3d`, `7d`, `14d`, `30d`, `60d`
- `mastery`

`hot1_sit_out` still exists internally, but only as the implementation detail for that one-quiz gap between `hot0` and `hot1`.

For fixed buckets `1d` and above, availability starts at midnight on the due day in the configured app timezone. Sub-day buckets still use exact elapsed time.

## Rules

- `unseen` + correct -> `mastery`
- any wrong answer -> `hot0`
- repeated wrong answers from `hot0` stay in `hot0`
- `hot0` + correct -> sit out one full quiz, then become `hot1`
- `hot1` + wrong -> `hot0`
- `hot1` + correct from `unseen` -> `1h`
- `hot1` + correct from a fixed bucket with one wrong in the cycle -> same bucket
- `hot1` + correct from a fixed bucket with more than one wrong in the cycle -> one bucket lower
- bucketed question + immediate correct -> next longer bucket
- highest bucket + correct -> `mastery`
- multiple-wrong recovery can only drop one bucket
- `1h` never drops below `1h`

Partial credit counts as wrong for scheduling. Final question order inside a quiz is still randomized after selection.
