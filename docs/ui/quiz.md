# UI: Quiz Page

See also:

- [UI index](../ui.md)
- [API study](../api/study.md)

The quiz page is the keyboard-first study surface.

## Active Session

- one unanswered question is active at a time
- answered cards remain visible
- `Enter` moves through multi-input answers and submits from the last field
- correct answers tint the card green
- incorrect answers tint the card red

## Feedback

- incorrect answers show all accepted answers in the grey feedback box
- correct answers that used a non-default accepted alternative expand that slot’s disabled input to all accepted answers
- correct answers that used the default accepted answer do not show a separate neutral feedback box

## Completed Session

- the completed session becomes the review surface
- the start-another-quiz action is prominent
- review actions live directly on answered cards
- correctly answered cards can be hidden to focus review
