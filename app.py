# app.py (Refactored for PostgreSQL & Auth)

import os
import logging
from datetime import datetime, date
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from flask_migrate import Migrate
from flask_login import LoginManager, login_user, current_user, logout_user, login_required
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from gemini import get_ai_suggestion, get_next_step

# Import modular components
from models import db, User, DailyLog, TopicHistory, UserProgress
from forms import RegistrationForm, LoginForm, ChangePasswordForm

# --- Basic App and Database Setup ---
app = Flask(__name__)

# Logging Configuration
if not app.debug:
    # Set the logging level for the production app logger
    # Standard output is used by default in production environments
    app.logger.setLevel(logging.INFO)
    app.logger.info('Smart Tracker startup')

# Security Config
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-key-change-this-in-prod')

# Step 2: Fix for Render/PostgreSQL connection strings
# This ensures compatibility with SQLAlchemy 1.4+ which requires 'postgresql://'
uri = os.getenv('DATABASE_URL')
if uri and uri.startswith("postgres://"):
    uri = uri.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = uri
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize extensions
db.init_app(app)
migrate = Migrate(app, db)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message_category = 'info'

# Rate Limiter Setup
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["2000 per day", "500 per hour"],
    storage_uri="memory://",
)

# --- Error Handlers ---
@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404

# @app.errorhandler(500)
# def internal_error(error):
#     db.session.rollback() # Ensure DB session is clean
#     app.logger.error(f"Server Error: {error}")
#     return render_template('500.html'), 500

# --- Login Manager Loader ---
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# --- Auth Routes ---

@app.route("/register", methods=['GET', 'POST'])
@limiter.limit("60 per minute")
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('Your account has been created! You can now log in', 'success')
        return redirect(url_for('login'))
    return render_template('register.html', title='Register', form=form)

@app.route("/login", methods=['GET', 'POST'])
@limiter.limit("60 per minute")
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and user.check_password(form.password.data):
            login_user(user, remember=form.remember.data)
            app.logger.info(f"User {user.username} logged in successfully.")
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('index'))
        else:
            app.logger.warning(f"Failed login attempt for username: {form.username.data}")
            flash('Login Unsuccessful. Please check username and password', 'danger')
    return render_template('login.html', title='Login', form=form)

@app.route("/logout")
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route("/profile", methods=['GET', 'POST'])
@login_required
def profile():
    form = ChangePasswordForm()
    if form.validate_on_submit():
        if not current_user.check_password(form.old_password.data):
            flash('Incorrect old password.', 'danger')
        else:
            current_user.set_password(form.new_password.data)
            db.session.commit()
            flash('Your password has been updated!', 'success')
            return redirect(url_for('profile'))
    return render_template('profile.html', title='Profile', form=form)


# --- Main Page & Tracker Routes ---
@app.route('/')
def index():
    return render_template('index.html')

# --- Dashboard & Progress Routes ---
@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html')

@app.route('/progress')
@login_required
def progress():
    # REFACTORED: Fetch logs only for current user
    logs_from_db = DailyLog.query.filter_by(user_id=current_user.id).order_by(DailyLog.log_date.desc()).all()
    logs = [
        {
            "date": log.log_date.strftime("%Y-%m-%d"),
            "notes": log.notes,
            "completed_tasks": log.completed_tasks
        } for log in logs_from_db
    ]
    return render_template("progress.html", logs=logs)

@app.route('/thm')
@login_required
def thm_dashboard():
    # Fetch user's completed rooms
    progress = UserProgress.query.filter_by(user_id=current_user.id, completed=True).all()
    completed_rooms = {p.room_id for p in progress}
    return render_template('thm.html', completed_rooms=completed_rooms)

# --- API Endpoints ---

@app.route('/api/toggle_room', methods=['POST'])
@login_required
def toggle_room():
    data = request.json
    room_id = data.get('room_id')
    completed = data.get('completed')

    if not room_id:
        return jsonify({"error": "Room ID required"}), 400

    progress = UserProgress.query.filter_by(user_id=current_user.id, room_id=room_id).first()

    if not progress:
        progress = UserProgress(user_id=current_user.id, room_id=room_id, completed=completed)
        db.session.add(progress)
    else:
        progress.completed = completed
    
    db.session.commit()
    return jsonify({"status": "success", "room_id": room_id, "completed": completed})

@app.route("/next_suggestion", methods=["POST"])
@login_required
def next_suggestion():
    data = request.get_json()
    topic = data.get("topic")
    level = data.get("level", "Basic")
    
    # Scoped to current user
    history_items = TopicHistory.query.filter_by(user_id=current_user.id, topic=topic.lower()).order_by(TopicHistory.id.desc()).limit(5).all()
    history = [item.entry for item in reversed(history_items)]

    suggestion = get_next_step(topic, history, level)
    
    if suggestion and "AI is busy" not in suggestion:
        new_history_entry = TopicHistory(
            topic=topic.lower(), 
            entry=f"({level}) {suggestion}",
            user_id=current_user.id
        )
        db.session.add(new_history_entry)
        db.session.commit()
        
    return jsonify({"suggestion": suggestion})

@app.route('/get_suggestion', methods=['POST'])
@login_required
def get_suggestion():
    data = request.json
    topic = data.get('topic')
    learning = data.get('learning')
    
    if not topic or not learning:
        return jsonify({"suggestion": "Topic and learning context are required."})

    # Scoped to current user
    history_items = TopicHistory.query.filter_by(user_id=current_user.id, topic=topic.lower()).order_by(TopicHistory.id.desc()).limit(5).all()
    history = [item.entry for item in reversed(history_items)]

    suggestion = get_ai_suggestion(topic, learning, history)
    return jsonify({"suggestion": suggestion})


@app.route('/save_log', methods=['POST'])
@login_required
def save_log():
    data = request.json
    date_str = data.get('date')
    log_date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()

    # Find log for this date AND this user
    log = DailyLog.query.filter_by(log_date=log_date_obj, user_id=current_user.id).first()

    if not log:
        log = DailyLog(log_date=log_date_obj, user_id=current_user.id)
        db.session.add(log)

    log.notes = data.get("notes")
    log.completed_tasks = data.get("completed_tasks", {})

    # Save topic history scoped to user
    for topic, info in data.get("completed_tasks", {}).items():
        if info.get("done") and info.get("task"):
            new_history_entry = TopicHistory(
                topic=topic.lower(), 
                entry=info["task"],
                user_id=current_user.id
            )
            db.session.add(new_history_entry)
    
    db.session.commit()
    return jsonify({"status": "success", "message": f"Log for {date_str} saved."})


@app.route('/load_log/<date_str>')
@login_required
def load_log(date_str):
    log_date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
    # Scope to user
    log = DailyLog.query.filter_by(log_date=log_date_obj, user_id=current_user.id).first()

    if log:
        return jsonify({
            "status": "found",
            "tasks": log.completed_tasks or {},
            "notes": log.notes or ""
        })
    return jsonify({"status": "not found"})


@app.route('/get_completed_htb')
@login_required
def get_completed_htb():
    items = TopicHistory.query.filter_by(topic='htb', user_id=current_user.id).all()
    completed_list = [item.entry for item in items]
    return jsonify({"completed": completed_list})


@app.route('/get_completed_bandit')
@login_required
def get_completed_bandit():
    items = TopicHistory.query.filter_by(topic='bandit', user_id=current_user.id).all()
    completed_list = [item.entry for item in items]
    return jsonify({"completed": completed_list})


@app.route('/analytics_data')
@login_required
def analytics_data():
    # Fetch logs ONLY for current user
    logs = DailyLog.query.filter_by(user_id=current_user.id).order_by(DailyLog.log_date.asc()).all()

    if not logs:
        return jsonify({
            "dates": [], "dailyLogs": [], "topicCounts": {},
            "longestStreak": 0, "currentStreak": 0, "thisMonth": 0
        })

    dates = [log.log_date.strftime("%Y-%m-%d") for log in logs]
    topic_counts = {}
    
    # Calculate strict date range for "This Month"
    today = date.today()
    start_of_month = today.replace(day=1)
    if today.month == 12:
        start_of_next_month = today.replace(year=today.year + 1, month=1, day=1)
    else:
        start_of_next_month = today.replace(month=today.month + 1, day=1)

    # DEBUG LOGGING (Requested by user)
    app.logger.info(f"--- Analytics Debug ---")
    app.logger.info(f"today: {today}")
    app.logger.info(f"start_of_month: {start_of_month}")
    app.logger.info(f"start_of_next_month: {start_of_next_month}")
    app.logger.info(f"All active dates: {dates}")

    this_month_count = 0
    
    for log in logs:
        # Count topics
        for key, task_obj in log.completed_tasks.items():
            task = task_obj.get("task") if isinstance(task_obj, dict) else task_obj
            if task:
                topic_counts[key] = topic_counts.get(key, 0) + 1
        
        # Count this month's logs using strict date range
        if start_of_month <= log.log_date < start_of_next_month:
            this_month_count += 1
            
    app.logger.info(f"Final this_month_count: {this_month_count}")
    app.logger.info(f"--- End Debug ---")

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

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=5000)
