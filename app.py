# app.py
from flask import Flask, render_template, request, jsonify
import os
import json
from datetime import datetime
# Centralized imports from your custom modules
from gemini import get_ai_suggestion, get_next_step
from tracker_memory import get_all_history, update_topic_history

app = Flask(__name__)
LOGS_DIR = "tracker_logs"

# Ensure the log directory exists
if not os.path.exists(LOGS_DIR):
    os.makedirs(LOGS_DIR)

# --- Main Page & Tracker Routes ---

@app.route('/')
def index():
    """Renders the main tracker page."""
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
    logs = []
    for file in sorted(os.listdir(LOGS_DIR)):
        if file.endswith(".json"):
            with open(os.path.join(LOGS_DIR, file)) as f:
                logs.append(json.load(f))
    return render_template("progress.html", logs=logs)

# --- CTF Dashboard Route (Re-added) ---

@app.route('/ctf')
def ctf_dashboard():
    """Renders the CTF dashboard page."""
    return render_template('ctf_dashboard.html')

# --- API Endpoints ---

@app.route("/next_suggestion", methods=["POST"])
def next_suggestion():
    data = request.get_json()
    topic = data.get("topic")
    # Get the level, default to "Basic" if not provided
    level = data.get("level", "Basic") 
    # Pass the level to the get_next_step function
    suggestion = get_next_step(topic, level) 
    return jsonify({"suggestion": suggestion})

@app.route('/get_suggestion', methods=['POST'])
def get_suggestion():
    """Gets a new task suggestion from the AI."""
    data = request.json
    topic = data.get('topic')
    learning = data.get('learning')
    
    if not topic or not learning:
        return jsonify({"suggestion": "Topic and learning context are required."})

    suggestion = get_ai_suggestion(topic, learning)
    return jsonify({"suggestion": suggestion})

@app.route('/save_log', methods=['POST'])
def save_log():
    data = request.json
    date_str = data.get('date')
    filename = os.path.join(LOGS_DIR, f"{date_str}.json")
    log_entry = {
        "date": date_str,
        "notes": data.get("notes"),
        "completed_tasks": data.get("completed_tasks")
    }
    with open(filename, 'w') as f:
        json.dump(log_entry, f, indent=4)

    for topic, info in data.get("completed_tasks", {}).items():
        if info.get("done") and info.get("task"):
            update_topic_history(topic, info["task"])

    return jsonify({"status": "success", "message": f"Log for {date_str} saved."})

@app.route('/load_log/<date>')
def load_log(date):
    filepath = os.path.join(LOGS_DIR, f"{date}.json")
    if os.path.exists(filepath):
        with open(filepath) as f:
            data = json.load(f)
        return jsonify({"status": "found", "tasks": data.get("completed_tasks", {}), "notes": data.get("notes", "")})
    return jsonify({"status": "not found"})

@app.route('/get_completed_htb')
def get_completed_htb():
    """API endpoint for CTF dashboard."""
    return jsonify({"completed": get_all_history("htb")})

@app.route('/get_completed_bandit')
def get_completed_bandit():
    """API endpoint for CTF dashboard."""
    return jsonify({"completed": get_all_history("bandit")})

@app.route('/analytics_data')
def analytics_data():
    from datetime import timedelta
    import glob

    files = sorted(glob.glob(f"{LOGS_DIR}/*.json"))
    dates = []
    topic_counts = {}
    streak = 0
    longest_streak = 0
    last_date_obj = None # Use a clearer variable name for the date object
    current_streak = 0

    for file in files:
        with open(file) as f:
            data = json.load(f)
            date_str = data['date']
            dates.append(date_str)

            for key, task_obj in data.get('completed_tasks', {}).items():
                task = task_obj.get("task") if isinstance(task_obj, dict) else task_obj
                if task:
                    topic_counts[key] = topic_counts.get(key, 0) + 1

            # Streak logic
            curr_date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
            if last_date_obj:
                if (curr_date_obj - last_date_obj).days == 1:
                    streak += 1
                elif (curr_date_obj - last_date_obj).days > 1:
                    # If there's a gap, the streak is broken
                    longest_streak = max(longest_streak, streak)
                    streak = 1 # Start a new streak
            else:
                streak = 1 # This is the very first log
            last_date_obj = curr_date_obj

    longest_streak = max(longest_streak, streak)
    
    # --- New logic to determine the current streak ---
    today = datetime.now().date()
    if last_date_obj and (today - last_date_obj).days <= 1:
        # If the last log was today or yesterday, the last calculated streak is the current one
        current_streak = streak

    return jsonify({
        "dates": dates,
        "dailyLogs": [1] * len(dates),
        "topicCounts": topic_counts,
        "longestStreak": longest_streak,
        "currentStreak": current_streak
    })

# --- Utility Routes ---

@app.route('/reset_memory')
def reset_memory():
    if app.debug:
        open("tracker_memory.json", "w").write("{}")
        return "Memory reset."
    else:
        return "This function is disabled in production mode.", 403

# --- App Execution ---

if __name__ == '__main__':
    # When you are finished with development, change debug=True to debug=False
    app.run(debug=False, host='0.0.0.0', port=5000)