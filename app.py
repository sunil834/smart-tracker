# app.py (Refactored for PostgreSQL)

import os
import subprocess
from datetime import datetime, date
from flask import Flask, render_template, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.dialects.postgresql import JSON
from apscheduler.schedulers.background import BackgroundScheduler

# We pass history to gemini now, so no direct db access is needed there
from gemini import get_ai_suggestion, get_next_step

# --- Basic App and Database Setup ---
app = Flask(__name__)

# This securely reads the DATABASE_URL environment variable you set in Render
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)


# --- Database Models ---
# Replaces the individual .json files in the tracker_logs/ directory
class DailyLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    log_date = db.Column(db.Date, unique=True, nullable=False, index=True)
    notes = db.Column(db.Text, nullable=True)
    completed_tasks = db.Column(JSON)

# Replaces the tracker_memory.json file
class TopicHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    topic = db.Column(db.String(100), nullable=False, index=True)
    entry = db.Column(db.String(500), nullable=False)

# This command creates the above tables in your database if they don't already exist.
# It's safe to run every time the app starts.
with app.app_context():
    db.create_all()


# --- Main Page & Tracker Routes ---
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/tracker')
def tracker():
    return render_template('tracker.html')

# --- Dashboard & Progress Routes ---
@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')

@app.route('/progress')
def progress():
    """REFACTORED: Fetches all logs from the database instead of files."""
    logs_from_db = DailyLog.query.order_by(DailyLog.log_date.desc()).all()
    # Convert DB objects to the dictionary format your template expects
    logs = [
        {
            "date": log.log_date.strftime("%Y-%m-%d"),
            "notes": log.notes,
            "completed_tasks": log.completed_tasks
        } for log in logs_from_db
    ]
    return render_template("progress.html", logs=logs)

@app.route('/ctf')
def ctf_dashboard():
    return render_template('ctf_dashboard.html')

# --- API Endpoints ---
# This endpoint now needs to fetch history from the DB before calling the AI
@app.route("/next_suggestion", methods=["POST"])
def next_suggestion():
    data = request.get_json()
    topic = data.get("topic")
    level = data.get("level", "Basic")
    
    # Fetch recent history from the database to provide context to the AI
    history_items = TopicHistory.query.filter_by(topic=topic.lower()).order_by(TopicHistory.id.desc()).limit(5).all()
    history = [item.entry for item in reversed(history_items)] # Pass a simple list of strings

    suggestion = get_next_step(topic, history, level)
    
    # Save the new suggestion to history so it's not repeated
    if suggestion and "AI is busy" not in suggestion:
        new_history_entry = TopicHistory(topic=topic.lower(), entry=f"({level}) {suggestion}")
        db.session.add(new_history_entry)
        db.session.commit()
        
    return jsonify({"suggestion": suggestion})

# This endpoint also now needs to fetch history from the DB
@app.route('/get_suggestion', methods=['POST'])
def get_suggestion():
    data = request.json
    topic = data.get('topic')
    learning = data.get('learning')
    
    if not topic or not learning:
        return jsonify({"suggestion": "Topic and learning context are required."})

    history_items = TopicHistory.query.filter_by(topic=topic.lower()).order_by(TopicHistory.id.desc()).limit(5).all()
    history = [item.entry for item in reversed(history_items)]

    suggestion = get_ai_suggestion(topic, learning, history) # Pass history to the function
    return jsonify({"suggestion": suggestion})


@app.route('/save_log', methods=['POST'])
def save_log():
    """REFACTORED: Saves a log entry to the database."""
    data = request.json
    date_str = data.get('date')
    log_date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()

    # Find if a log for this date already exists
    log = DailyLog.query.filter_by(log_date=log_date_obj).first()

    if not log:
        # If it doesn't exist, create a new one
        log = DailyLog(log_date=log_date_obj)
        db.session.add(log)

    # Update the log's data
    log.notes = data.get("notes")
    log.completed_tasks = data.get("completed_tasks", {})

    # Save the topic history (replaces update_topic_history)
    for topic, info in data.get("completed_tasks", {}).items():
        if info.get("done") and info.get("task"):
            new_history_entry = TopicHistory(topic=topic.lower(), entry=info["task"])
            db.session.add(new_history_entry)
    
    db.session.commit() # Commit all changes to the database
    return jsonify({"status": "success", "message": f"Log for {date_str} saved."})


@app.route('/load_log/<date_str>')
def load_log(date_str):
    """REFACTORED: Loads a log entry from the database."""
    log_date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
    log = DailyLog.query.filter_by(log_date=log_date_obj).first()

    if log:
        return jsonify({
            "status": "found",
            "tasks": log.completed_tasks or {},
            "notes": log.notes or ""
        })
    return jsonify({"status": "not found"})


@app.route('/get_completed_htb')
def get_completed_htb():
    """REFACTORED: Fetches HTB history from the database."""
    items = TopicHistory.query.filter_by(topic='htb').all()
    completed_list = [item.entry for item in items]
    return jsonify({"completed": completed_list})


@app.route('/get_completed_bandit')
def get_completed_bandit():
    """REFACTORED: Fetches Bandit history from the database."""
    items = TopicHistory.query.filter_by(topic='bandit').all()
    completed_list = [item.entry for item in items]
    return jsonify({"completed": completed_list})


@app.route('/analytics_data')
def analytics_data():
    """REFACTORED: Calculates analytics from database data."""
    logs = DailyLog.query.order_by(DailyLog.log_date.asc()).all()

    if not logs:
        return jsonify({
            "dates": [], "dailyLogs": [], "topicCounts": {},
            "longestStreak": 0, "currentStreak": 0, "thisMonth": 0
        })

    dates = [log.log_date.strftime("%Y-%m-%d") for log in logs]
    topic_counts = {}
    
    # Count this month's activities
    current_month = date.today().month
    current_year = date.today().year
    this_month_count = 0
    
    for log in logs:
        # Count topics
        for key, task_obj in log.completed_tasks.items():
            task = task_obj.get("task") if isinstance(task_obj, dict) else task_obj
            if task:
                topic_counts[key] = topic_counts.get(key, 0) + 1
        
        # Count this month's logs
        if log.log_date.month == current_month and log.log_date.year == current_year:
            this_month_count += 1

    # Streak Logic (existing code)
    longest_streak = 0
    current_streak = 0
    if logs:
        streak = 1
        longest_streak = 1
        for i in range(1, len(logs)):
            if (logs[i].log_date - logs[i-1].log_date).days == 1:
                streak += 1
            else:
                longest_streak = max(longest_streak, streak)
                streak = 1
        longest_streak = max(longest_streak, streak)

        # Calculate current streak
        last_log_date = logs[-1].log_date
        today = date.today()
        if (today - last_log_date).days <= 1:
            current_streak = streak
    
    return jsonify({
        "dates": dates,
        "dailyLogs": [1] * len(dates),
        "topicCounts": topic_counts,
        "longestStreak": longest_streak,
        "currentStreak": current_streak,
        "thisMonth": this_month_count
    })

def run_backup_job():
    """
    This function is called by the scheduler to execute the backup script.
    """
    print("Scheduler triggered: Starting backup job...")
    try:
        # We run the backup.sh script using a subprocess
        # The environment variables from Render will be available to this script
        subprocess.run(["bash", "backup.sh"], check=True, capture_output=True, text=True)
        print("Backup job completed successfully.")
    except subprocess.CalledProcessError as e:
        # Log any errors from the script
        print(f"Backup job failed.")
        print(f"Error output:\n{e.stderr}")

# Initialize the scheduler to run in the background
scheduler = BackgroundScheduler()
# Schedule the run_backup_job to run every day at 05:05 UTC
scheduler.add_job(run_backup_job, 'cron', hour=5, minute=5)
# Start the scheduler
scheduler.start()

# --- App Execution ---
if __name__ == '__main__':
    # For local development, you might want debug=True
    # For production on Render, debug MUST be False.
    app.run(debug=False, host='0.0.0.0', port=5000)