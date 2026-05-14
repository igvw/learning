# API: Study and Stats

See also:

- [API index](../api.md)
- [UI quiz](../ui/quiz.md)
- [UI stats](../ui/stats.md)
- [Spaced repetition](../spaced-repetition.md)

## Quiz Sessions

### `POST /api/quiz-sessions`

Starts a quiz session for the authenticated actor.

Practical request shape:

```json
{
  "module_id": 12,
  "count": 10
}
```

Response includes:

- session `id`
- selected `module_id`
- `completed_at`
- `items[]`

Each quiz item includes:

- question and module identifiers
- module instruction
- prompt and question type
- rank
- normalized `type_config`
- verification and provenance fields
- current answer state fields

### `POST /api/quiz-sessions/{session_id}/items/{item_id}/submit`

Submits one answered question.

Practical request shape:

```json
{
  "answers": ["white nile", "blue nile"]
}
```

Response includes:

- `item_id`
- `is_correct`
- `score_earned`
- `score_possible`
- `slot_results`
- `canonical_answers`
- `default_answers`
- `accepted_answer_groups`
- `matched_default_answers`
- `session_completed`
- `submitted_answer`

Feedback fields:

- `canonical_answers` is the compatibility field
- `default_answers` is the first accepted answer for each slot
- `accepted_answer_groups` contains the full accepted answers for each slot in authoring order
- `matched_default_answers` marks whether each submitted slot matched that slot’s first accepted answer

## Stats

### `GET /api/stats`

Returns stats for the selected scope and authenticated actor.

Supported query params:

- `module_id`
- `review_only`

Frontend behavior note:

- the shipped stats page requests full-scope stats and switches between non-review question buckets and scoped pending revision proposals client-side
- `review_only` remains a supported backend query parameter for direct API callers

The response contains:

- `schedule_timezone`
- `summary`
- `recent_sessions`
- `study_blocks`
- `questions`
- `revision_proposals`

`recent_sessions` remains quiz-session based. `study_blocks` is activity based: it groups answered questions into blocks where each consecutive answer is less than 30 minutes after the previous one and starts a new block after a 30+ minute gap. It returns the latest 20 blocks with answer count, score totals, accuracy, duration, and answers-per-minute metrics. The stats UI uses the latest 10 for the compact graph and all 20 in the detail overlay.

`revision_proposals` contains scoped pending revision/delete proposals: admins receive all pending proposals in the selected scope, while regular users receive only their own pending proposals.

Each question row includes:

- current question content
- attempts and accuracy
- `first_asked_at`
- `last_asked_at`
- verification and provenance fields
- recent aggregated incorrect answers
- derived schedule state

Schedule fields include:

- `bucket`
- `logical_bucket` (`unseen`, fixed bucket labels from `1h` through `60d`, or `mastery`)
- `recovery_streak`
- `interval_step`
- `last_incorrect_at`
- `next_due_at`

`next_due_at` uses exact elapsed timestamps for `<1d` buckets. For `1d` and above, it is the start of the due calendar day in the configured app schedule timezone.
