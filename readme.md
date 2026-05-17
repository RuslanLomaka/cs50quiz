# QuizForger

QuizForger is my CS50 Web capstone project. It is a Django-based web application for creating, editing, and playing custom quizzes in the browser.

The project is currently self-hosted by me on my own Raspberry Pi 3 hardware, served as a Django/Gunicorn application and published to the internet through Cloudflare Tunnel.

The core idea behind the project is simple: instead of forcing the author to manually build every quiz question from scratch, QuizForger gives them a guided workflow. They can generate a quiz with an AI tool, paste the result into the app, and then refine it further through a browser-based editor. The finished quiz can then be played interactively in the browser, scored immediately, and tracked through attempts and average score statistics.

At its current stage, the application supports:

- user signup, login, and logout
- authenticated quiz creation
- browser-based quiz editing
- owner-side quiz deletion
- public quiz playing
- attempt tracking and average score tracking
- per-question explanations shown after checking answers
- single-answer and multiple-answer questions
- optional per-question source links
- a dark mode that follows system preference and can also be toggled manually

## Distinctiveness and Complexity

I believe this project satisfies the capstone requirement for both distinctiveness and complexity.

In terms of distinctiveness, QuizForger is not a clone of any of the course projects. It is not a social network, commerce site, email client, or wiki. Its focus is different: it is a lightweight authoring platform for quizzes, with a workflow built around AI-assisted generation plus manual browser-based refinement. That combination is the main identity of the project. The app is not just a quiz player. It also includes author-side tooling, ownership, editing, and validation rules that make quiz creation practical for a real user.

Another distinctive part of the project is the editing model. The app originally used quiz JSON as the main source of content, and that idea is still present, but the user experience no longer depends on hand-editing raw JSON after creation. The author can now create a quiz from generated JSON and then fine-tune it with a visual in-browser editor that exposes titles, questions, answer choices, correct answers, and optional sources. This makes the project more than a simple CRUD interface.

In terms of complexity, the project combines several moving parts that work together:

- Django views, routing, authentication, and database models
- database-backed storage for quiz content and attempts
- frontend JavaScript for rendering quizzes, handling both radio-button and checkbox question types, scoring answers, saving attempts, and displaying explanations and sources
- a structured browser editor that serializes form state back into valid quiz JSON
- permission rules so only owners or staff can edit quizzes
- source/reference support for question verification after quiz completion

There is also a separation between the create flow and the edit flow. Creating a quiz is intentionally simple and import-oriented: the user pastes generated quiz data into the app. Editing is more advanced: the user works through a browser UI with question cards, answer controls, source fields, validation messages, and focused error handling. That split took extra design work, but it made the app much easier to use.

For these reasons, I think the project goes beyond a minimal CRUD application and meets the spirit of the capstone.

## Files and Structure

The project is organized as a single Django project with one main application:

- `manage.py`
  Django management entry point.

- `config/settings.py`
  Main Django settings, including installed apps, authentication backend, redirects, database settings, and static configuration.

- `config/urls.py`
  Root URL configuration for the whole project.

- `quizforger/models.py`
  Defines the main data models:
  - `Quiz` stores quiz metadata, ownership, timestamps, and quiz content in a JSON field.
  - `Attempt` stores quiz results for users or guests.

- `quizforger/views.py`
  Contains the main application views:
  - quiz listing
  - personal quiz listing
  - quiz play page
  - API endpoint for quiz data
  - API endpoint for attempt creation
  - create quiz flow
  - edit quiz flow
  - delete quiz action
  - signup view

- `quizforger/urls.py`
  App-level routes for quizzes and account-related pages.

- `quizforger/storage.py`
  Contains helper functions for creating and updating quiz records.

- `quizforger/forms.py`
  Signup form and email-focused authentication form.

- `quizforger/auth_backends.py`
  Custom authentication backend that supports email-based login while still allowing username-based admin login.

- `quizforger/admin.py`
  Registers `Quiz` and `Attempt` with Django admin.

- `quizforger/templates/quizforger/base.html`
  Shared layout, navigation, theme behavior, and global styling.

- `quizforger/templates/quizforger/create.html`
  Quiz creation page with AI prompt helper and JSON import field.

- `quizforger/templates/quizforger/editor.html`
  Browser-based structured editor for updating existing quizzes.

- `quizforger/templates/quizforger/list.html`
  Quiz list page used for both all quizzes and a user’s own quizzes.

- `quizforger/templates/quizforger/quiz.html`
  Quiz play page.

- `quizforger/templates/registration/login.html`
  Login page.

- `quizforger/templates/registration/signup.html`
  Signup page.

- `quizforger/static/quizforger/quiz.js`
  Client-side quiz logic for:
  - rendering questions and answers
  - handling single-answer and multiple-answer question modes
  - shuffling answers
  - scoring
  - attempt submission
  - explanation display after checking answers
  - inline source display after completion

- `quizforger/static/quizforger/app.css`
  Main application stylesheet for shared layout, theme styling, dark mode appearance, and editor/list page presentation.

- `quizforger/migrations/`
  Django migrations for the database schema.

- `db.sqlite3`
  SQLite development database.

## How to Run

1. Make sure Python is installed.
2. Open a terminal in the project folder.
3. Install Django if it is not already installed:

```bash
pip install -r requirements.txt
```

4. Apply migrations:

```bash
python manage.py migrate
```

5. Start the development server:

```bash
python manage.py runserver
```

6. Open the app in your browser:

```text
http://127.0.0.1:8000/quizzes
```

## How to Use the App

1. Create an account or log in.
2. Open `Create`.
3. Copy the AI prompt shown on the page.
4. Paste it into an AI tool of your choice.
5. Copy the generated quiz result and paste it into QuizForger.
6. Save the quiz.
7. If needed, open the edit page and fine-tune the quiz in the browser.
8. Open the quiz and play it.

The app supports both quick quiz import and manual browser editing. In the edit page, the user can:

- change the quiz title
- edit question text
- edit per-question explanations
- edit answer text
- mark correct answers
- choose whether a question uses one correct answer or multiple correct answers
- add or remove answer options
- add or remove sources
- delete an owned quiz from the list view

The editor validates common mistakes before saving. For example, it checks that each question has text, each answer has text, there are at least two answer options, and the number of correct answers matches the selected answer mode.

## How to Test

Here are the main features that should be tested manually:

### Authentication

- create a new account
- log in with email and password
- log out
- verify that quiz creation requires login

### Quiz creation

- open the create page
- paste valid quiz JSON
- save it
- confirm the quiz appears in the list

### Quiz editing

- open `My quizzes`
- click `Edit`
- change the title, question text, or answers
- save
- confirm the updated version is shown when playing the quiz

### Quiz ownership actions

- open `My quizzes`
- delete one of your own quizzes
- confirm it disappears from the list
- verify that another user does not get the same delete option

### Quiz play

- open a quiz
- answer the questions
- click `Check answers`
- verify score calculation
- verify that explanations appear under the relevant questions after completion
- verify that sources appear under the relevant questions after completion
- verify that multiple-answer questions use checkboxes
- verify that single-answer questions use radio buttons
- verify that attempts with fewer than 50% of questions answered do not count

### Stats

- complete a quiz more than once
- return to the quiz list
- confirm attempts and average score update

### Theme

- test the manual dark mode toggle
- test the app in both light and dark mode

### Mobile responsiveness

Use browser device emulation and test at least:

- quiz list
- personal quiz list
- create page
- edit page
- login/signup
- quiz play page

## Current Limitations

This is still a development-stage project, so there are some known limitations:

- password reset by email is not implemented yet
- quizzes can currently be attempted multiple times by the same user
- the app relies on AI-generated input quality during quiz creation
- the project uses SQLite in development
- there is no deployment configuration included yet

## Small Roadmap

I intentionally want to keep the roadmap realistic and close to the current app.

Possible next improvements:

- add password reset by email
- add stronger password validation and clearer password help text
- add an option to limit quizzes to one attempt per user
- add a more structured deployment setup for production hosting

## Author

Ruslan Lomaka
