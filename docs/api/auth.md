# API: Authentication and Sessions

See also:

- [API index](../api.md)
- [UI auth](../ui/auth.md)

## `GET /api/health`

Returns:

- `status`
- `instance_key`
- `bootstrap_required`

## `POST /api/auth/bootstrap-admin`

Creates the first admin account when no admin exists yet, then starts a session.

Practical request shape:

```json
{
  "handle": "admin",
  "display_name": "Admin",
  "password": "password123"
}
```

## `POST /api/auth/login`

Signs in a real account and sets the session cookie.

## `POST /api/auth/logout`

Clears the current session cookie.

## `GET /api/auth/me`

Returns the current authenticated actor:

- `id`
- `handle`
- `display_name`
- `role` (`admin`, `user`, `demo`)
- `is_demo`
- `created_at`

## `POST /api/auth/demo-session`

Starts an ephemeral demo session.
