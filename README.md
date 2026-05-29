# Smart Tracker

An intelligent learning and progress tracker with AI-powered suggestions. Track your progress across topics like cybersecurity, programming, and CTF challenges with streak badges and personalized learning recommendations powered by Google Gemini.

## Features

- **User Authentication** - Secure registration and login with password management
- **Daily Progress Logging** - Log completed tasks and notes for each day
- **Topic Management** - Create and manage custom topics (Python, Linux, Hacking, CTF, etc.)
- **AI-Powered Suggestions** - Get personalized next steps and learning suggestions via Google Gemini API
- **Streak Tracking** - Build and maintain streaks with milestone badges (🌱 Seedling → 🌟 Legend)
- **Analytics Dashboard** - Visualize your progress with charts and activity summaries
- **HackTheBox & Bandit Integration** - Track completed rooms and challenges
- **Async Job Processing** - Non-blocking AI requests with Redis-backed job queue
- **Rate Limiting** - Distributed rate limiting with Redis for API protection

## Technology Stack

- **Backend:** Flask, Flask-SQLAlchemy, Flask-Login, Flask-Migrate
- **Database:** PostgreSQL
- **Frontend:** HTML, CSS, JavaScript
- **AI Integration:** Google Generative AI (Gemini Flash)
- **Caching & Job Queue:** Redis
- **Rate Limiting:** Flask-Limiter
- **Deployment:** Gunicorn

## Prerequisites

- Python 3.7+
- PostgreSQL database
- Redis (optional, for rate limiting and async jobs)
- Google Gemini API key

## Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/sunil834/smart-tracker.git
   cd smart-tracker
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Environment Configuration:**
   Create a .env file in the root directory:
   ```env
   SECRET_KEY=your-super-secret-key
   DATABASE_URL=postgresql://user:password@localhost:5432/smart_tracker
   GEMINI_API_KEY=your-gemini-api-key
   # Optional: enables Redis-backed rate limiting and AI job storage.
   # If omitted, the app falls back to in-memory storage.
   REDIS_URL=redis://localhost:6379/0
   AI_WORKER_THREADS=4
   ```

4. **Initialize the database:**
   ```bash
   flask db upgrade
   ```

5. **Run the application:**
   ```bash
   python app.py
   ```

   Or with Gunicorn for production:
   ```bash
   gunicorn app:app
   ```

   The app will be available at `http://localhost:5000`

## Usage

### Authentication
- **Register** at `/register` to create a new account
- **Login** at `/login` with your credentials
- **Change Password** in your profile at `/profile`

### Daily Logging
1. Navigate to the home page
2. Select a date and enter completed tasks for different topics
3. Add notes for context
4. Autosave tracks your progress

### Topic Management
- Create custom topics via `/topics`
- Topics are user-scoped (private to each user)
- Delete topics (associated history is preserved, goals are removed)

### AI Suggestions
- **Get Next Step:** Requests AI to suggest the next learning task based on your history and difficulty level
- **Get Suggestion:** Asks AI for a recommendation on what to learn next for a specific topic
- Requests are async and processed via background workers

### Progress Analytics
- **Dashboard** (`/dashboard`): Visual overview of your streaks and badges
- **Progress** (`/progress`): Paginated historical view of your daily logs
- **Analytics API** (`/analytics_data`): Detailed stats including:
  - Current and longest streaks
  - Badge tier and milestone info
  - Topic counts and activity by date
  - This month's activity count

### Badge Tiers

Earn badges by maintaining daily streaks:

| Emoji | Badge | Days Required |
|-------|-------|---------------|
| 🌱 | Seedling | 1 |
| 🔥 | On Fire | 7 |
| ⚡ | Momentum | 15 |
| 🚀 | Moonshot | 30 |
| 🏆 | Champion | 60 |
| 🔮 | Quarter | 90 |
| 🌊 | Half Year | 180 |
| 🌙 | 3 Quarters | 270 |
| 🌟 | Legend | 365 |

### Integrations

**HackTheBox Tracking:**
- Navigate to `/thm` to track completed rooms
- Toggle room completion status
- View all completed rooms

**Bandit Challenges:**
- Access your completed Bandit levels via the API
- Tracked as topic history entries

## API Endpoints

### Authentication
- `POST /register` - Create new user account
- `POST /login` - Login to account
- `GET /logout` - Logout

### Topics
- `GET /topics` - List user's topics
- `POST /topics` - Create new topic
- `DELETE /topics/<id>` - Delete topic

### Logs & Progress
- `GET /load_log/<date>` - Load tasks for a specific date (YYYY-MM-DD)
- `PATCH /api/log/<date>` - Update log for a date
- `POST /save_log` - Save daily log with tasks
- `GET /analytics_data` - Get analytics and streak data
- `GET /progress` - View paginated progress history

### AI Features
- `POST /get_suggestion` - Request AI suggestion (returns job_id)
- `POST /next_suggestion` - Request next learning step (returns job_id)
- `GET /ai_job/<job_id>` - Poll async job status and result

### Challenge Tracking
- `POST /api/toggle_room` - Mark HackTheBox room as complete/incomplete
- `GET /get_completed_htb` - Get completed HTB rooms
- `GET /get_completed_bandit` - Get completed Bandit levels

## Database Schema

- **User** - User accounts with authentication
- **DailyLog** - Daily task logs with completed_tasks (JSON) and notes
- **Topic** - User-created learning topics
- **TopicHistory** - Timestamped history of completed tasks per topic
- **UserProgress** - Tracks room/challenge completions
- **Goal** - Learning goals with target counts and periods
- **Badge** - Earned streak badges per user

## Configuration

### Rate Limiting
- Default: 2000 requests per day, 500 per hour
- Uses Redis for distributed limiting across multiple workers
- Falls back to local storage if Redis unavailable

### AI Job Processing
- Async job queue with ThreadPoolExecutor
- Redis TTL: 10 minutes for job storage
- Configurable worker threads via `AI_WORKER_THREADS` env variable
- Timeout: 8 seconds per Gemini API request

### Database Connection Pooling
- Pool pre-ping enabled for connection stability
- Pool recycled every 5 minutes
- Auto-reconnects on connection closure

## Error Handling

- **404 Pages:** Custom error page for not found
- **500 Pages:** Automatic session rollback on server errors
- **Database Errors:** Graceful fallback with logging
- **AI Timeouts:** User-friendly fallback messages

## Development

### Running Locally
```bash
export FLASK_ENV=development
export FLASK_DEBUG=1
python app.py
```

### Database Migrations
```bash
flask db init              # Initialize migration folder
flask db migrate           # Create new migration
flask db upgrade           # Apply migrations
```

## Logging

The application logs to standard output. In production:
- Log level: INFO
- Available logs include user actions, database warnings, and AI job failures
- Debug logging in analytics calculations (see `/analytics_data`)

## Security Features

- Password hashing with Werkzeug
- Session-based authentication with Flask-Login
- CSRF protection with Flask-WTF
- Rate limiting to prevent abuse
- User data isolation (queries scoped to current_user)
- SQL injection prevention via SQLAlchemy ORM

## Deployment

Deploy to Render, Heroku, or any WSGI-compatible platform:

1. Set environment variables on your platform
2. Use `gunicorn app:app` as the start command
3. Ensure PostgreSQL and Redis are available
4. Run migrations: `flask db upgrade`

---

Built with ❤️ for learners and achievers.
