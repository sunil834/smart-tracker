# 🧠 Smart Tracker

**Smart Tracker** is a robust, AI-assisted learning and task-tracking dashboard built with Flask. It helps developers, hackers, and students log their daily progress, maintain learning streaks, and receive context-aware next steps powered by Google's Gemini AI.

## ✨ Key Features

- **Daily Progress Logging**: Log your completed tasks, notes, and tags in a timeline-style archive with a clean UI.
- **Streak & Analytics Engine**: Visualize your activity, longest/current streaks, and monthly counts. Earn milestones and badges (from 🌱 Seedling to 🌟 Legend).
- **🤖 AI-Powered Mentor (Gemini)**: Get actionable, difficulty-tailored next steps based on your specific learning history (e.g., Python, CTFs, Linux).
- **Topic Management**: Create customizable learning tracks, set targets, and track granular history over time.
- **Async & Scalable**: Uses Redis for distributed rate-limiting and asynchronous AI job execution to keep the UI snappy.
- **Secure User Auth**: Built-in registration, login, and profile management using Flask-Login and Werkzeug security.

## 🛠️ Tech Stack

- **Backend**: Python, Flask, SQLAlchemy, Flask-Migrate
- **Database**: PostgreSQL (via DATABASE_URL)
- **Caching/State**: Redis (for API rate-limiting via lask-limiter and async AI jobs)
- **AI Integration**: Google Generative AI (Gemini Flash)
- **Frontend**: HTML5, custom CSS (modern dark-themed UI), vanilla JavaScript
- **Package Manager**: [uv](https://github.com/astral-sh/uv)

## 🚀 Getting Started

### Prerequisites
- Python 3.10+
- [uv](https://github.com/astral-sh/uv) installed
- PostgreSQL database
- Redis server (local or cloud)
- [Google Gemini API Key](https://aistudio.google.com/app/apikey)

### Installation & Setup

1. **Clone the repository:**
   `ash
   git clone https://github.com/sunil834/smart-tracker.git
   cd smart-tracker
   `

2. **Install dependencies:**
   Fast installation using the uv package manager:
   `ash
   uv sync
   `

3. **Environment Configuration:**
   Create a .env file in the root directory:
   `env
   SECRET_KEY=your-super-secret-key
   DATABASE_URL=postgresql://user:password@localhost:5432/smart_tracker
   GEMINI_API_KEY=your-gemini-api-key
   REDIS_URL=redis://localhost:6379/0
   AI_WORKER_THREADS=4
   `

4. **Initialize the Database:**
   Apply the latest schema migrations:
   `ash
   uv run -- flask db upgrade
   `
   *(Note: The app also attempts to lazily bootstrap tables on the first run via db.create_all())*

5. **Run the Application:**
   `ash
   uv run -- python app.py
   `
   
The app will be available at http://localhost:5000.

## 📂 Project Structure

- pp.py: Main Flask application, route definitions, and Redis-backed AI job runner.
- models.py: SQLAlchemy database models (User, DailyLog, TopicHistory, Badge, etc.).
- gemini.py: Integration with Google Generative AI for tailored learning suggestions.
- 	emplates/ & static/: Jinja2 templates and modern CSS/JS for the responsive dashboard frontend.
- migrations/: Alembic directory for database schema tracking.

## 🤝 Contributing
Contributions, issues, and feature requests are welcome! Feel free to check the [issues page](https://github.com/sunil834/smart-tracker/issues).

## 📝 License
This project is licensed under the MIT License.
