# API: Content, Accounts, Moderation, and Questions

See also:

- [API index](../api.md)
- [UI manage](../ui/manage.md)
- [Database](../database.md)

## Modules

### `GET /api/modules/tree`

Returns the visible module tree for the current actor.

Each node includes:

- `id`
- `title`
- `slug`
- `full_slug`
- `instruction`
- `admin_verified`
- `moderation_status`
- `created_by_user_id`
- `creator_display_name`
- `children`

### `POST /api/modules`

Creates one module node.

Practical request shape:

```json
{
  "title": "nouns_to_english",
  "parent_id": 12,
  "instruction": "Translate each Norwegian noun into English."
}
```

The frontend builds slash-path `mkdir -p` behavior by making repeated calls.

### `PATCH /api/modules/{module_id}`

Updates one existing leaf module.

Practical request shape:

```json
{
  "title": "verbs_to_english",
  "instruction": "Translate each Norwegian verb into English."
}
```

Leaf-module rename behavior:

- leaf-module rename keeps the same module id
- only the selected leaf segment is renamed
- parent paths remain unchanged

### `DELETE /api/modules/{module_id}`

Admin-only. Hard-deletes a module subtree when it is safe to remove.

Delete behavior:

- deletes the selected module and descendant modules
- deletes contained questions only when they have no attempts
- rejects deletion when any contained question has attempts or is in an active quiz session

### `GET /api/modules/export`

Admin-only. Downloads the full verified shared content tree as one zip archive.

Export behavior:

- response type is `application/zip`
- filename is `modules-export.zip`
- archive paths are rooted at `modules-export/content/modules/`
- every verified module gets `module.yaml`
- every verified leaf gets `questions.qml`
- `questions.qml` lines are emitted in shared order (`rank ASC, id ASC`)
- pending, rejected, and viewer-specific overlay content is excluded

This is a manual content export for portability and inspection, not a database backup.

## Users

### `GET /api/users`

Admin-only. Returns the current real account list.

### `POST /api/users`

Admin-only. Creates one real account.

Practical request shape:

```json
{
  "handle": "ignazio",
  "display_name": "Ignazio",
  "role": "user",
  "password": "password123"
}
```

### `PATCH /api/users/{user_id}`

Admin-only. Updates one real account role.

Practical request shape:

```json
{
  "role": "admin"
}
```

### `POST /api/users/{user_id}/password`

Admin-only. Replaces one real account password.

## Contributions and Moderation

### `GET /api/contributions/me`

Returns the current regular user’s active contribution queue:

- pending modules
- pending uploaded questions

Pending revision/delete proposals live on the stats Review surface instead of this Manage-page contribution queue. Rejected modules are excluded from this user-facing payload.

### `GET /api/moderation/queue`

Admin-only. Returns:

- `pending_modules`
- `rejected_modules`
- pending question uploads

Pending revision/delete proposals are returned by `GET /api/stats` for the selected scope. Admins moderate them from the stats Review surface through `POST /api/moderation/question-revisions/{proposal_id}`.

### `POST /api/moderation/modules/{module_id}`

### `DELETE /api/moderation/modules/{module_id}`

Admin-only. Deletes one rejected unverified module and its entire unverified descendant subtree. If any descendant module is verified, the delete is rejected instead of partially deleting the tree.

### `POST /api/moderation/questions/{question_id}`

### `POST /api/moderation/question-revisions/{proposal_id}`

Admin-only moderation actions. Request shape:

```json
{
  "action": "approve",
  "note": "",
  "edited_revision": {
    "module_id": 12,
    "prompt": "updated prompt",
    "question_type": "single_text",
    "rank": 4,
    "accepted_answers": [["updated answer"]],
    "segments": [],
    "reset_stats": true
  }
}
```

`edited_revision` is optional and only valid when `action` is `approve`. It lets an admin open a pending revision in the shared question drawer, edit the proposed content, and approve that edited version immediately. Approving a delete proposal with `edited_revision` keeps the question and applies the edited revision.

## Questions

### `POST /api/questions`

Creates a new question.

Role behavior:

- admins create verified questions immediately
- regular users create pending questions that are immediately usable only for themselves and visible to admins

Practical request fields:

- `module_id`
- `prompt`
- `question_type`
- `rank` (accepted for compatibility; create placement is server-managed append order)
- `accepted_answers`
- optional `segments`

### `POST /api/questions/{question_id}/revisions`

Role behavior:

- admins update the verified question in place and can optionally reset history-derived stats
- regular users editing a verified question create or update a personal revision proposal instead
- regular users editing their own pending uploaded question update that pending row directly

Regular-user verified-question revisions must contain an actual content change. Unchanged revision payloads return `422`.

### `DELETE /api/questions/{question_id}`

Role behavior:

- admins delete the question immediately
- regular users delete only their own pending uploaded questions immediately
- regular users deleting a verified question create or update a personal delete request proposal instead

### `DELETE /api/questions/{question_id}/revisions/mine`

Deletes the current user’s pending revision/delete proposal for the question. This removes the item from stats Review mode and returns the original question to normal quiz eligibility based on its existing history-derived schedule.
