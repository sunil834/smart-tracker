# app.py (Refactored for PostgreSQL)

import os
import subprocess
from datetime import datetime, date
from flask import Flask, render_template, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.dialects.postgresql import JSON
import json # Still needed for processing request data

# --- Daily Backup Scheduler ---
from apscheduler.schedulers.background import BackgroundScheduler

# Centralized imports from your custom modules
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
    """CORRECTED: Properly calculates streaks from actual daily logs."""
    logs = DailyLog.query.order_by(DailyLog.log_date.asc()).all()
    
    if not logs:
        return jsonify({
            "topicCounts": {}, 
            "longestStreak": 0, 
            "currentStreak": 0, 
            "heatmap_data": [],
            "activity_map": {}
        })

    # Create activity map - True for days with ANY completed tasks
    activity_map = {}
    active_dates = []
    
    for log in logs:
        date_str = log.log_date.strftime("%Y-%m-%d")
        # Check if ANY task was completed that day
        has_activity = False
        
        if hasattr(log, 'completed_tasks') and log.completed_tasks:
            for key, task_data in log.completed_tasks.items():
                if isinstance(task_data, dict):
                    if task_data.get("done", False) or task_data.get("task", "").strip():
                        has_activity = True
                        break
                elif isinstance(task_data, str) and task_data.strip():
                    has_activity = True
                    break
        
        activity_map[date_str] = has_activity
        if has_activity:
            active_dates.append(log.log_date)

    # Sort active dates for proper streak calculation
    active_dates.sort()

    # Calculate current streak
    current_streak = 0
    if active_dates:
        today = date.today()
        
        # Find the most recent active date
        last_active = active_dates[-1]
        
        # Only count as current streak if within last 2 days
        if (today - last_active).days <= 1:
            current_streak = 1
            
            # Count backwards for consecutive days
            for i in range(len(active_dates) - 2, -1, -1):
                if (active_dates[i + 1] - active_dates[i]).days == 1:
                    current_streak += 1
                else:
                    break

    # Calculate longest streak
    longest_streak = 0
    if active_dates:
        temp_streak = 1
        longest_streak = 1
        
        for i in range(1, len(active_dates)):
            if (active_dates[i] - active_dates[i-1]).days == 1:
                temp_streak += 1
                longest_streak = max(longest_streak, temp_streak)
            else:
                temp_streak = 1

    # Count topics
    topic_counts = {}
    for log in logs:
        if hasattr(log, 'completed_tasks') and log.completed_tasks:
            for key, task_obj in log.completed_tasks.items():
                if isinstance(task_obj, dict) and task_obj.get("task"):
                    topic_counts[key] = topic_counts.get(key, 0) + 1

    # Prepare heatmap data
    heatmap_data = []
    for date_str, is_active in activity_map.items():
        if is_active:
            heatmap_data.append({"date": date_str, "value": 1})

    return jsonify({
        "topicCounts": topic_counts,
        "longestStreak": longest_streak,
        "currentStreak": current_streak,
        "heatmap_data": heatmap_data,
        "activity_map": activity_map,
        "current_month": datetime.now().month - 1,
        "current_year": datetime.now().year
    })

# --- Daily Backup Job ---
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