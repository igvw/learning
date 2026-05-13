# UI: Manage Page

See also:

- [UI index](../ui.md)
- [API content](../api/content.md)

The third route is role-aware.

## Admin View

Admins see:

- compact top-row summary cards for `Accounts`, `Modules`, `Import`, and `Export`
- overlay-based account creation, role updates, and password reset
- overlay-based global module editing, path-based creation, and safe module deletion
- overlay-based manual full-content export
- overlay-based QML import
- moderation summary cards for pending modules and pending uploaded questions

Module management behavior:

- `Module path` is a slash-separated full path with existing-path suggestions
- existing path segments are reused automatically when creating missing descendants
- module deletion is admin-only and is rejected when attempted or active quiz content depends on the subtree

Moderation behavior:

- each moderation category opens in its own overlay
- the `Modules` moderation overlay opens with `Pending` and `Rejected` summary cards before drilling into either list
- rejected modules move out of the pending list, stay admin-visible, and can be either approved or hard-deleted
- the pending uploaded questions overlay groups rows by module and supports bulk approve/reject per module table
- question revision/delete proposal moderation lives on the stats page Review card

## Regular User View

Regular users see:

- a compact `Modules` summary card that opens pending-module creation and editing
- one wide `My contributions` summary card
- a browsable contributions overlay with pending `Modules` and `Uploaded questions`
- pending revision/delete proposals live on the stats page Review card
