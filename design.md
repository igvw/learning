# Learning app

I will make a comprehensive design prompt that includes planning instructions and skills.md and planning.

## This design document

Should be a minimal design plan to recreate the app from scratch. It should be converted to a README.md, which has table schemas and more comprehensive information.

## Prompt

I want to build a web app used for learning basic facts with codex. I want to keep it as simple as possible while supporting different modules. The actual app should be completely independent of the content.

Data layout:

- the questions table is most important and needs to be considered most
  - There should be different kinds of questions:
    - multiple correct answers from which a single answer is expected
    - multiple required answers from which all must be given
    - more to be implemented later
  - Questions belong to modules and submodules
  - Questions need to be revised
    - marked disabled
    - new ID for the revised question
    - new question points back to old question so revision history can be seen
  - questions need unique, but editable rank per module, that stays consistent when a question is revised
- modules and submodules
  - should have all app variance for each module

- progress tracking
  - sessions
    - how long and when a session was started
  - progress for each question

Pages and functionality:

- Quizz page
  - asks a fixed amount of questions
  - should scroll vertically as questions are answered
  - quick review: after each question highlight question
    - red for wrong and green for correct
    - show all correct answers below the question
    - highlight the rows green for correct and red for incorrect

- Review page
  - Once quiz is complete
  - show total score
  - a table of all questions, their correct answer(s), the answer given, a button to mark question for revision

- Stats page
  - Show graph for last 10 quizzes
  - show table of all questions for selected module/submodule
    - unique id
    - rank (a default ordering, think 1.1.1 for chapter 1, section 1, question 1 this is unique to each module)
    - question
    - answers
    - how often they were asked
    - percentage of times correct
    - when they were last asked
    - revision button to revise the question
  - highlight questions flagged for revision in orange
  - show a box with list of questions flagged for revision at the top of the stats page

- Revision page
  - both question and answer should be revisable
  - a list of incorrect answers seen
  - a checkbox for wether stats needs to be invalidated (default on)
  - a rank selector that will increment all questions equal to or below the selected rank without updating their ID's. Don't update ID of edited question if only this field changed.
  - a way to see question history:
    - list of links
    - uneditable version of revision page with irrelevant options greyed out

- Creation page
  - accessed from floating plus icon on stats page.
  - select existing(sub)module from dropdown
  - ability to create new module
  - need to be able to create all types of questions
  - rank selector, default auto-increment

Modules and submodules:

- hierarchical structure (e.g. Biology->plants)
- Select from hamburger menu on the top left
- Should be able to select parent module and submodules to train individual chapters or entire bundle of work
- view stats for selected module only.
- There needs to be a modules metadata table that handles the UI variation in app (question titles etc)
- The structure of the questions and metadata table needs to be simple to give to an LLM to generate module content in a ./module directory

pay special attention to keyboard navigation throughout the app. I want to complete a quiz without lifting my hands off the keyboard

Suggested tech stack:

- Flask
- SQLite
- Jinja templates
- Vanilla javascript or htmx

testing:

- add normal python tests
- make a ./app.sh that will run the webapp
- seed the project with 2 modules that contain at least one of each type of question

## iterate on the prompt

### Instruction

I want to iterate on the above minimal design document to ensure it is as simple and comprehensive as possible. Output raw markdown only with only required edits.

## codex

I want to plan this a bit better in this chat and then proceed to codex. Once we are ready to go to codex, please provide me with tips for plan mode, skills and other context md file tips and a prompt.
