# UI: Manage Page

See also:

- [UI index](../ui.md)
- [API content](../api/content.md)

The third route is role-aware.

## Admin View

Admins see:

- compact top-row summary cards for `Accounts`, `Modules`, `Import`, and `Export`
- overlay-based account creation, role updates, and password reset
- overlay-based global module editing
- overlay-based manual full-content export
- overlay-based QML import
- moderation summary cards for pending modules, pending uploaded questions, and question revision/delete proposals

Moderation behavior:

- each moderation category opens in its own overlay
- the pending uploaded questions overlay groups rows by module and supports bulk approve/reject per module table
- the pending revisions overlay opens with module cards, then drills into one module at a time with collapsed change sections
- each revision row keeps all question details in one `Changes` snapshot
- clicking a revision snapshot opens the shared question drawer in moderation-review mode, and saving approves the edited revision immediately
- pending revisions support bulk approve/reject per expanded change section

## Regular User View

Regular users see:

- a compact `Modules` summary card that opens pending-module creation and editing
- one wide `My contributions` summary card
- a browsable contributions overlay with `Modules`, `Uploaded questions`, and active `Revisions`
- read-only revision detail using the same snapshot or diff card style as admin moderation, without moderation actions
