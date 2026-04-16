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
- fixed buckets: `1h`, `3h`, `6h`, `12h`, `1d`, `3d`, `7d`, `14d`, `30d`, `60d` (`1h` is the lowest fixed bucket)
- `mastery`: no longer served by the scheduler

## Transitions

- `unseen` + wrong -> `hot0`
- `unseen` + correct -> `mastery`
- `hot0` + correct -> `hot1`
- unseen-origin `hot1` skips the sit-out and can be served again in the very next quiz
- non-unseen `hot1` in the immediately preceding quiz -> `hot1_sit_out`
- `hot1` + correct -> shortest bucket, or back to its remembered bucket, once it is served again
- `hot1` + wrong -> `hot0`
- bucketed question + correct -> next longer bucket
- highest bucket + correct -> `mastery`
- `1h` + wrong -> `hot0`
- higher bucket + first wrong -> wait one full quiz, then retry from that same bucket
- bucket retry + correct -> back to the original bucket
- bucket retry + wrong -> `hot0`

If a question came from a bucket, then later recovered out of hotness:

- one failure in that retry cycle -> return to the original bucket
- more than one failure after the retry was served -> return one bucket lower
- the shortest bucket stays at the shortest bucket

This means a miss from the lowest fixed bucket goes back into hot recovery immediately and can reappear in every quiz until answered correctly. Unseen-origin recovery is even more aggressive: once the learner gets the first recovery answer right, the question is still served again immediately for confirmation instead of sitting out one quiz.

Partial credit counts as wrong for scheduling. Final question order inside a quiz is still randomized after selection.
