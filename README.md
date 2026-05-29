# Smart Tracker

Smart Tracker is a Flask app for logging daily learning tasks, tracking streaks, and getting AI-powered next-step suggestions.

## Features
- Daily task logging with notes
- Progress and streak analytics
- AI suggestions powered by Gemini
- Optional Redis-backed rate limiting and async AI jobs

## Tech Stack
- Flask + Flask-Login
- SQLAlchemy + Flask-Migrate
- PostgreSQL (via `DATABASE_URL`)
- Redis (optional, for rate limiting and AI job state)
- Google Generative AI (Gemini)

## Setup (using `uv`)
1. Create and activate a virtual environment.
2. Install dependencies with `uv` (uses the active environment's lockfile):

```bash
uv sync
```

3. Configure environment variables (example `.env`):

```bash
SECRET_KEY=change-me
DATABASE_URL=postgresql://user:pass@host:5432/dbname
GEMINI_API_KEY=your-key
REDIS_URL=redis://localhost:6379/0
AI_WORKER_THREADS=4
```

## Run
Start the app with `uv run`:

```bash
uv run -- python app.py
```

The app runs on `http://localhost:5000` by default.

## Git
After reviewing changes, commit and push to GitHub:

```bash
git add -A
git commit -m "Remove scripts folder; update README to use uv"
git push origin main
```

