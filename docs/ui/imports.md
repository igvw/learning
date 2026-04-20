# UI: Import Drawer and Upload Flow

See also:

- [UI index](../ui.md)
- [API imports](../api/imports.md)
- [Question Markup DSL](../question-markup.md)

The import drawer is a review-and-commit drawer for one leaf module.

## Drawer Behavior

- paste or load QML text
- validate rows into one review table
- show exact duplicate counts in the summary above the table
- show duplicate, relocation, invalid, and conflict rows together in the same table
- keep original physical line numbers visible and color-coded
- let editable rows change QML directly in the table
- show answer chips grouped by answer slot
- color-code answer chips by source:
  - current answer
  - imported answer
  - manually added answer
- persist the import session in `sessionStorage` so refresh restores the drawer state

## Save Behavior

- save submits the current edited rows
- the frontend saves committable rows in 50-row chunks
- while a chunked upload is active, the review rows become read-only status rows
- partial success keeps the drawer open, removes already committed rows, and revalidates the remainder
- blocking rows stay highlighted red until edited or removed
- the drawer can be hidden while an upload keeps running in the current tab
- a compact header upload-status pill reopens the drawer

## Access

- the QML upload path is admin-only
