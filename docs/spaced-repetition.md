# Spaced Repetition

The scheduler uses two ideas at once:

- `hotness` for short-term recovery
- fixed time buckets for longer-term review

## Serving priority

1. `hot0`
2. `hot1`
3. due bucketed questions, shortest bucket first
4. unseen questions

Questions marked for review are skipped entirely. Mastery questions are ignored for now.

## State summary

- `unseen`: never answered
- `hot0`: answered incorrectly and needs immediate follow-up
- `hot1`: answered correctly once after `hot0`
- `hot1_sit_out`: a `hot1` question that must miss one full quiz before it can be shown again
- fixed buckets: `1h`, `3h`, `6h`, `12h`, `1d`, `3d`, `7d`, `14d`
- `mastery`: no longer served by the scheduler

## Transitions

- `unseen` + wrong -> `hot0`
- `unseen` + correct -> `mastery`
- `hot0` + correct -> `hot1`
- `hot1` in the immediately preceding quiz -> `hot1_sit_out`
- `hot1` after one full intervening quiz + correct -> shortest bucket, or back to its remembered bucket
- `hot1` + wrong -> `hot0`
- bucketed question + correct -> next longer bucket
- highest bucket + correct -> `mastery`
- bucketed question + first wrong -> wait one full quiz, then retry from that same bucket
- bucket retry + correct -> back to the original bucket
- bucket retry + wrong -> `hot0`

If a question came from a bucket, then later recovered out of hotness:

- one failure in that retry cycle -> return to the original bucket
- more than one failure after the retry was served -> return one bucket lower
- the shortest bucket stays at the shortest bucket

Partial credit counts as wrong for scheduling. Final question order inside a quiz is still randomized after selection.
