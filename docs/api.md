# Learning App API

This document indexes the API surface by capability.

See also:

- [Overview](overview.md)
- [Database](database.md)
- [UI](ui.md)

## Conventions

- all app routes live under `/api`
- request and response bodies are JSON unless otherwise noted
- `question_type` is one of `single_text`, `multi_text`, `ordered_multi`, `inline_cloze`, `bundle`
- authenticated routes use the server-side session cookie

## Route Groups

- [Authentication and sessions](api/auth.md)
  Healthcheck, first-admin bootstrap, sign-in, and sign-out.
- [Content, accounts, moderation, and questions](api/content.md)
  Modules, users, contribution queues, moderation actions, question authoring, and revision proposals.
- [Study and stats](api/study.md)
  Quiz-session start/submit behavior, feedback fields, and stats payloads.
- [Imports](api/imports.md)
  QML import format, validation results, and commit behavior.

Use the grouped docs above for detailed request and response behavior.
