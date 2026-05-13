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
- correct answers expand that slot’s disabled input to all accepted answers
- answered cards show `Suggest change`, which opens the shared question editor without moving the question to Review until an actual revision/delete proposal is saved

## Completed Session

- the start-another-quiz action is prominent
- suggestion actions live directly on answered cards
- correctly answered cards can be hidden to focus review
