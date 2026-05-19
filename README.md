# 🎯 Interview Preparation Tracker

A full-stack web application that helps students organise and monitor their technical interview preparation.

## Features

- **Dashboard** — overall and per-category progress bars at a glance
- **Topics** — add, edit, delete, and toggle completion of prep topics across four categories
- **My Notes** — write and save notes per topic; attach photos from camera or gallery; inline lightbox viewer
- **My Tasks** — personal task manager with due dates, priorities, and status tracking
- **Progress** — detailed per-category topic lists with completion stats
- **User Auth** — register / login with bcrypt-hashed passwords and Flask sessions
- **Admin Panel** — view all students, their task progress, and delete accounts

## Categories

| Category | Description |
|---|---|
| 🧮 Aptitude | Number series, profit & loss, probability, time & work |
| 💻 Programming | Algorithms, data structures, coding patterns |
| 🌳 Data Structures | Arrays, trees, graphs, dynamic programming |
| 🎤 Mock Interviews | Behavioural questions, system design, mock sessions |

## Tech Stack

- **Backend** — Python 3.11, Flask, Flask-SQLAlchemy
- **Database** — SQLite (auto-created on first run)
- **Auth** — bcrypt + Flask sessions
- **Frontend** — Vanilla HTML / CSS / JavaScript (no framework)

## Project Structure

```
artifacts/interview-tracker/
├── app.py                  # Main Flask app — routes, models, seed data
├── requirements.txt        # Python dependencies
├── templates/              # Jinja2 HTML templates
│   ├── base.html
│   ├── dashboard.html
│   ├── topics.html
│   ├── notes.html
│   ├── tasks.html
│   ├── progress.html
│   ├── admin.html
│   └── ...
└── static/
    ├── css/style.css       # All styles
    ├── js/main.js          # AJAX toggle, task status, notes JS
    └── uploads/notes/      # User-uploaded note images (gitignored)
```

## Getting Started

```bash
# 1. Clone the repo
git clone https://github.com/Vibhudhisravani517/interview-prep-tracker.git
cd interview-prep-tracker

# 2. Install dependencies
pip install flask flask-sqlalchemy bcrypt werkzeug

# 3. Run the app
cd artifacts/interview-tracker
python app.py
```

Visit `http://localhost:5000` — the SQLite database and seed topics are created automatically on first run.

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `SESSION_SECRET` | `dev-secret-key-change-me` | Flask session signing key — change in production |
| `PORT` | `5000` | Server port |

## Screenshots

> Dashboard · Topics · My Notes (with image upload) · Progress · Admin Panel

---

Built with ❤️ for interview prep success.
