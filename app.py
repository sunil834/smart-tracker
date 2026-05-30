# app.py (Refactored for PostgreSQL & Auth)

import json
import os
import uuid
import logging
from datetime import datetime, date
from concurrent.futures import ThreadPoolExecutor
from threading import Lock
from typing import Any
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from flask_migrate import Migrate
from flask_login import (
    LoginManager,
    login_user,
    current_user,
    logout_user,
    login_required,
)
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import redis
from sqlalchemy import inspect
from sqlalchemy.exc import SQLAlchemyError
from gemini import get_ai_suggestion, get_next_step

# Import modular components
from models import db, User, DailyLog, TopicHistory, UserProgress, Topic, Goal, Badge
from forms import RegistrationForm, LoginForm, ChangePasswordForm

# --- Basic App and Database Setup ---
app = Flask(__name__)

# Logging Configuration
if not app.debug:
    # Set the logging level for the production app logger
    # Standard output is used by default in production environments
    app.logger.setLevel(logging.INFO)
    app.logger.info("Smart Tracker startup")

# Security Config
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-key-change-this-in-prod")

# Step 2: Fix for Render/PostgreSQL connection strings
uri = os.getenv("DATABASE_URL")
if uri and uri.startswith("postgres://"):
    uri = uri.replace("postgres://", "postgresql://", 1)

app.config["SQLALCHEMY_DATABASE_URI"] = uri
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# --- ADD THIS BLOCK HERE ---
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_pre_ping": True,  # This detects the "closed unexpectedly" error and reconnects automatically
    "pool_recycle": 300,  # Refreshes connections every 5 mins to keep them fresh
}

# Initialize extensions
db.init_app(app)
migrate = Migrate(app, db)
login_manager = LoginManager(app)
login_manager.login_view = "login"
login_manager.login_message_category = "info"

# Ensure any newly added tables exist even if migrations have not been applied yet.
with app.app_context():
    try:
        db.create_all()
    except Exception as exc:
        app.logger.warning("Database bootstrap skipped: %s", exc)

# Prefer in-memory rate limiting by default so local development does not depend
# on Redis DNS/network availability. Set LIMITER_STORAGE_URI explicitly to use Redis.
redis_url = os.environ.get("REDIS_URL") or os.environ.get("REDIS_URI")
limiter_storage_uri = os.environ.get("LIMITER_STORAGE_URI", "memory://")
if limiter_storage_uri == "memory://":
    app.logger.info("Using in-memory rate limiting.")
elif limiter_storage_uri.startswith("redis://") or limiter_storage_uri.startswith(
    "rediss://"
):
    try:
        redis.Redis.from_url(limiter_storage_uri, decode_responses=True).ping()
    except Exception:
        app.logger.warning(
            "Redis unavailable for rate limiting; falling back to in-memory storage."
        )
        limiter_storage_uri = "memory://"
else:
    app.logger.warning(
        "Unsupported LIMITER_STORAGE_URI provided; falling back to in-memory storage."
    )
    limiter_storage_uri = "memory://"
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["2000 per day", "500 per hour"],
    storage_uri=limiter_storage_uri,
)

# Async AI job execution state
ai_job_store: redis.Redis | None = None
ai_job_redis_url = redis_url or ""
if ai_job_redis_url:
    try:
        ai_job_store = redis.Redis.from_url(ai_job_redis_url, decode_responses=True)
        ai_job_store.ping()
    except Exception:
        ai_job_store = None
        app.logger.warning(
            "Redis unavailable for AI jobs; using local in-memory fallback."
        )
else:
    app.logger.info("REDIS_URL not set; using in-memory AI job storage.")

ai_job_executor = ThreadPoolExecutor(
    max_workers=int(os.environ.get("AI_WORKER_THREADS", "4"))
)
ai_job_lock = Lock()
ai_job_cache: dict[str, dict[str, Any]] = {}
ai_job_ttl_seconds = 10 * 60


BADGE_TIERS = [
    {"key": "seedling", "emoji": "🌱", "name": "Seedling", "min": 3},
    {"key": "on_fire", "emoji": "🔥", "name": "On Fire", "min": 7},
    {"key": "momentum", "emoji": "⚡", "name": "Momentum", "min": 15},
    {"key": "moonshot", "emoji": "🚀", "name": "Moonshot", "min": 30},
    {"key": "champion", "emoji": "🏆", "name": "Champion", "min": 60},
    {"key": "quarter", "emoji": "🔮", "name": "Quarter", "min": 90},
    {"key": "half_year", "emoji": "🌊", "name": "Half Year", "min": 180},
    {"key": "three_q", "emoji": "🌙", "name": "3 Quarters", "min": 270},
    {"key": "legend", "emoji": "🌟", "name": "Legend", "min": 365},
]


def get_badge(streak):
    badge = None
    for t in BADGE_TIERS:
        if streak >= t["min"]:
            badge = t
    return badge or {"key": "none", "emoji": "", "name": ""}


def milestone_label(streak):
    if streak >= 365:
        extra = streak - 365
        if extra == 0:
            return "1 year milestone!"
        yrs, rem = divmod(extra, 365)
        return f"{yrs}yr {rem}d streak" if yrs else f"{streak} days · Legend"
    if streak >= 270:
        return f"{streak} days (9 months+)"
    if streak >= 180:
        return f"{streak} days (6 months+)"
    if streak >= 90:
        return f"{streak} days (3 months+)"
    return None


def check_and_award_badges(user_id, streak):
    newly = []
    for t in BADGE_TIERS:
        if streak >= t["min"]:
            exists = Badge.query.filter_by(user_id=user_id, tier=t["key"]).first()
            if not exists:
                db.session.add(Badge(user_id=user_id, tier=t["key"]))
                newly.append(t["key"])
    if newly:
        db.session.commit()
    return newly


def _calculate_streak_summary(user_id):
    logs = (
        DailyLog.query.filter_by(user_id=user_id)
        .order_by(DailyLog.log_date.asc())
        .all()
    )

    longest_streak = 0
    current_streak = 0

    if logs:
        streak = 1
        longest_streak = 1
        for i in range(1, len(logs)):
            if (logs[i].log_date - logs[i - 1].log_date).days == 1:
                streak += 1
            else:
                longest_streak = max(longest_streak, streak)
                streak = 1
        longest_streak = max(longest_streak, streak)

        last_log_date = logs[-1].log_date
        if (date.today() - last_log_date).days <= 1:
            current_streak = streak

    return {
        "logs": logs,
        "longest_streak": longest_streak,
        "current_streak": current_streak,
    }


def _format_streak_display(current_streak, badge, milestone):
    if current_streak <= 0:
        return "0 days streak"

    tier_label = " ".join(
        part for part in (badge["emoji"], badge["name"]) if part
    ).strip()
    streak_label = (
        milestone or f"{current_streak} day{'s' if current_streak != 1 else ''} streak"
    )

    if tier_label:
        return f"{tier_label} · {streak_label}"
    return streak_label


def _next_badge_tier(current_streak):
    for tier in BADGE_TIERS:
        if current_streak < tier["min"]:
            return {
                "key": tier["key"],
                "emoji": tier["emoji"],
                "name": tier["name"],
                "min": tier["min"],
                "days_left": tier["min"] - current_streak,
            }
    return None


def _streak_progress_percent(current_streak):
    next_tier = _next_badge_tier(current_streak)
    if not next_tier:
        return 100

    previous_min = 0
    for tier in BADGE_TIERS:
        if tier["min"] < next_tier["min"] and current_streak >= tier["min"]:
            previous_min = tier["min"]

    span = max(next_tier["min"] - previous_min, 1)
    progress = int(((current_streak - previous_min) / span) * 100)
    return max(0, min(progress, 100))


@app.context_processor
def inject_streak_context():
    current_streak = 0

    if current_user.is_authenticated:
        try:
            current_streak = _calculate_streak_summary(current_user.id)[
                "current_streak"
            ]
        except Exception as exc:
            app.logger.warning("Could not load streak context: %s", exc)

    badge = get_badge(current_streak)
    milestone = milestone_label(current_streak)
    next_tier = _next_badge_tier(current_streak)
    return {
        "current_streak": current_streak,
        "streak_badge_tier": badge["key"],
        "streak_badge_emoji": badge["emoji"],
        "streak_badge_name": badge["name"],
        "streak_milestone_label": milestone,
        "streak_display_text": _format_streak_display(current_streak, badge, milestone),
        "streak_next_tier_name": next_tier["name"] if next_tier else None,
        "streak_next_tier_emoji": next_tier["emoji"] if next_tier else None,
        "streak_next_tier_days_left": next_tier["days_left"] if next_tier else None,
        "streak_progress_percent": _streak_progress_percent(current_streak),
    }


def _ai_job_key(job_id):
    return f"ai-job:{job_id}"


def _store_ai_job(job_id, payload):
    data = {"job_id": job_id, **payload}
    serialized = json.dumps(data)
    if ai_job_store is not None:
        ai_job_store.setex(_ai_job_key(job_id), ai_job_ttl_seconds, serialized)
        return
    with ai_job_lock:
        ai_job_cache[job_id] = data


def _load_ai_job(job_id):
    if ai_job_store is not None:
        raw = ai_job_store.get(_ai_job_key(job_id))
        if not raw:
            return None
        return json.loads(raw if isinstance(raw, str) else raw.decode("utf-8"))
    with ai_job_lock:
        return ai_job_cache.get(job_id)


def _create_ai_job(kind, payload):
    job_id = uuid.uuid4().hex
    _store_ai_job(
        job_id,
        {"status": "queued", "kind": kind, "result": None, "error": None, **payload},
    )
    ai_job_executor.submit(_run_ai_job, job_id)
    return job_id


def _run_ai_job(job_id):
    job = _load_ai_job(job_id)
    if not job:
        return

    with app.app_context():
        try:
            _store_ai_job(job_id, {**job, "status": "running"})

            user_id = int(job["user_id"])
            topic = job["topic"]
            kind = job["kind"]

            history_items = (
                TopicHistory.query.filter_by(user_id=user_id, topic=topic.lower())
                .order_by(TopicHistory.created_at.desc())
                .limit(5)
                .all()
            )
            history = [item.entry for item in reversed(history_items)]

            if kind == "suggestion":
                result_text = get_ai_suggestion(topic, job.get("learning", ""), history)
            else:
                result_text = get_next_step(topic, history, job.get("level", "Basic"))

            if kind == "next_step" and result_text and "AI is busy" not in result_text:
                topic_obj = Topic.query.filter_by(user_id=user_id, name=topic).first()
                new_history_entry = TopicHistory(
                    topic=topic.lower(),
                    topic_id=topic_obj.id if topic_obj else None,
                    entry=f"({job.get('level', 'Basic')}) {result_text}",
                    user_id=user_id,
                )
                db.session.add(new_history_entry)
                db.session.commit()

            _store_ai_job(
                job_id,
                {
                    **job,
                    "status": "complete",
                    "result": result_text,
                    "error": None,
                },
            )
        except Exception as exc:
            db.session.rollback()
            _store_ai_job(
                job_id,
                {
                    **job,
                    "status": "failed",
                    "result": None,
                    "error": str(exc),
                },
            )


# --- Error Handlers ---
@app.errorhandler(404)
def not_found_error(error):
    return render_template("404.html"), 404


@app.errorhandler(500)
def internal_error(error):
    try:
        db.session.rollback()
    except Exception:
        pass

    app.logger.exception("Server Error", exc_info=True)

    if request.accept_mimetypes.best == "application/json":
        return jsonify(error="Internal server error"), 500
    return render_template("500.html"), 500


# --- Login Manager Loader ---
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# --- Auth Routes ---


@app.route("/register", methods=["GET", "POST"])
@limiter.limit("60 per minute")
def register():
    if current_user.is_authenticated:
        return redirect(url_for("index"))
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash("Your account has been created! You can now log in", "success")
        return redirect(url_for("login"))
    return render_template("register.html", title="Register", form=form)


@app.route("/login", methods=["GET", "POST"])
@limiter.limit("60 per minute")
def login():
    if current_user.is_authenticated:
        return redirect(url_for("index"))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and user.check_password(form.password.data):
            login_user(user, remember=form.remember.data)
            app.logger.info(f"User {user.username} logged in successfully.")
            next_page = request.args.get("next")
            return redirect(next_page) if next_page else redirect(url_for("index"))
        else:
            app.logger.warning(
                f"Failed login attempt for username: {form.username.data}"
            )
            flash("Login Unsuccessful. Please check username and password", "danger")
    return render_template("login.html", title="Login", form=form)


@app.route("/logout")
def logout():
    logout_user()
    return redirect(url_for("index"))


@app.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    form = ChangePasswordForm()
    if form.validate_on_submit():
        if not current_user.check_password(form.old_password.data):
            flash("Incorrect old password.", "danger")
        else:
            current_user.set_password(form.new_password.data)
            db.session.commit()
            flash("Your password has been updated!", "success")
            return redirect(url_for("profile"))
    return render_template("profile.html", title="Profile", form=form)


# --- Main Page & Tracker Routes ---
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/topics", methods=["GET", "POST"])
@login_required
def manage_topics():
    if request.method == "POST":
        data = request.get_json() or {}
        name = (data.get("name") or "").strip()
        if not name:
            return jsonify({"error": "Topic name required"}), 400
        # Prevent duplicates per user
        existing = Topic.query.filter_by(user_id=current_user.id, name=name).first()
        if existing:
            return jsonify(
                {
                    "status": "exists",
                    "topic": {"id": existing.id, "name": existing.name},
                }
            )
        t = Topic(name=name, user_id=current_user.id)
        db.session.add(t)
        db.session.commit()
        return jsonify({"status": "created", "topic": {"id": t.id, "name": t.name}})

    # GET -> list topics
    topics = (
        Topic.query.filter_by(user_id=current_user.id).order_by(Topic.name.asc()).all()
    )
    return jsonify({"topics": [{"id": t.id, "name": t.name} for t in topics]})


@app.route("/topics/<int:topic_id>", methods=["DELETE"])
@login_required
def delete_topic(topic_id):
    topic = Topic.query.filter_by(id=topic_id, user_id=current_user.id).first()
    if not topic:
        return jsonify({"error": "Topic not found"}), 404

    try:
        inspector = inspect(db.engine)

        # Remove goal rows when the table/columns exist in the live schema.
        goal_table = Goal.__tablename__
        if inspector.has_table(goal_table):
            goal_columns = {col["name"] for col in inspector.get_columns(goal_table)}
            if {"user_id", "topic_id"}.issubset(goal_columns):
                Goal.query.filter_by(user_id=current_user.id, topic_id=topic.id).delete(
                    synchronize_session=False
                )

        # Keep history rows but detach them from deleted topic only when topic_id exists.
        history_table = TopicHistory.__tablename__
        if inspector.has_table(history_table):
            history_columns = {
                col["name"] for col in inspector.get_columns(history_table)
            }
            if {"user_id", "topic_id"}.issubset(history_columns):
                TopicHistory.query.filter_by(
                    user_id=current_user.id, topic_id=topic.id
                ).update({"topic_id": None}, synchronize_session=False)

        db.session.delete(topic)
        db.session.commit()
    except SQLAlchemyError as exc:
        db.session.rollback()
        app.logger.warning("Failed to delete topic %s: %s", topic_id, exc)
        return jsonify({"error": "Could not delete topic"}), 500

    return jsonify({"status": "deleted", "topic_id": topic_id})


# --- Dashboard & Progress Routes ---
@app.route("/dashboard")
@login_required
def dashboard():
    return render_template("dashboard.html")


@app.route("/progress")
@login_required
def progress():
    # Server-side pagination for historical logs (20 records per page)
    page = request.args.get("page", 1, type=int)
    per_page = 20

    pagination = (
        DailyLog.query.filter_by(user_id=current_user.id)
        .order_by(DailyLog.log_date.desc())
        .paginate(page=page, per_page=per_page, error_out=False)
    )

    logs_from_db = pagination.items
    logs = [
        {
            "date": log.log_date.strftime("%Y-%m-%d"),
            "notes": log.notes,
            "completed_tasks": log.completed_tasks,
        }
        for log in logs_from_db
    ]
    return render_template(
        "progress.html",
        logs=logs,
        pagination=pagination,
        current_page=page,
        per_page=per_page,
    )


@app.route("/thm")
@login_required
def thm_dashboard():
    # Fetch user's completed rooms
    progress = UserProgress.query.filter_by(
        user_id=current_user.id, completed=True
    ).all()
    completed_rooms = {p.room_id for p in progress}
    return render_template("thm.html", completed_rooms=completed_rooms)


# --- API Endpoints ---


@app.route("/api/toggle_room", methods=["POST"])
@login_required
def toggle_room():
    data = request.json
    room_id = data.get("room_id")
    completed = data.get("completed")

    if not room_id:
        return jsonify({"error": "Room ID required"}), 400

    progress = UserProgress.query.filter_by(
        user_id=current_user.id, room_id=room_id
    ).first()

    if not progress:
        progress = UserProgress(
            user_id=current_user.id, room_id=room_id, completed=completed
        )
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
    if not topic:
        return jsonify({"error": "Topic required"}), 400

    job_id = _create_ai_job(
        "next_step",
        {
            "user_id": current_user.id,
            "topic": topic,
            "level": level,
        },
    )
    return jsonify({"job_id": job_id, "status": "queued"}), 202


@app.route("/get_suggestion", methods=["POST"])
@login_required
def get_suggestion():
    data = request.json
    topic = data.get("topic")
    learning = data.get("learning")

    if not topic or not learning:
        return jsonify({"error": "Topic and learning context are required."}), 400

    job_id = _create_ai_job(
        "suggestion",
        {
            "user_id": current_user.id,
            "topic": topic,
            "learning": learning,
        },
    )
    return jsonify({"job_id": job_id, "status": "queued"}), 202


@app.route("/ai_job/<job_id>", methods=["GET"])
@login_required
def get_ai_job(job_id):
    job = _load_ai_job(job_id)
    if not job or int(job.get("user_id", 0)) != current_user.id:
        return jsonify({"error": "Job not found"}), 404

    response = {
        "job_id": job_id,
        "status": job.get("status", "queued"),
    }
    if job.get("status") == "complete":
        response["suggestion"] = job.get("result")
    elif job.get("status") == "failed":
        response["error"] = job.get("error") or "AI job failed"

    return jsonify(response)


def _save_daily_log(date_str, payload, record_history=True):
    log_date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
    data = payload or {}

    # Find log for this date AND this user.
    log = DailyLog.query.filter_by(
        log_date=log_date_obj, user_id=current_user.id
    ).first()

    if not log:
        log = DailyLog(log_date=log_date_obj, user_id=current_user.id)
        db.session.add(log)

    completed_tasks = data.get("completed_tasks", {})
    log.notes = data.get("notes", "")
    log.completed_tasks = completed_tasks

    # Keep topic history, but avoid duplicate entries when autosave replays the same state.
    if record_history and isinstance(completed_tasks, dict):
        for topic, info in completed_tasks.items():
            if not isinstance(info, dict):
                continue
            if info.get("done") and info.get("task"):
                history_text = info["task"]
                existing_history = TopicHistory.query.filter_by(
                    user_id=current_user.id,
                    topic=topic.lower(),
                    entry=history_text,
                ).first()
                if existing_history:
                    continue

                topic_obj = Topic.query.filter_by(
                    user_id=current_user.id, name=topic
                ).first()
                new_history_entry = TopicHistory(
                    topic=topic.lower(),
                    topic_id=topic_obj.id if topic_obj else None,
                    entry=history_text,
                    user_id=current_user.id,
                )
                db.session.add(new_history_entry)

    db.session.commit()

    streak_summary = _calculate_streak_summary(current_user.id)
    newly_unlocked = check_and_award_badges(
        current_user.id, streak_summary["current_streak"]
    )

    return log, streak_summary, newly_unlocked


@app.route("/api/log/<date_str>", methods=["PATCH"])
@login_required
def patch_log(date_str):
    data = request.get_json(silent=True) or {}

    try:
        _, _, newly_unlocked = _save_daily_log(date_str, data, record_history=True)
    except ValueError:
        return jsonify({"error": "Invalid date format. Use YYYY-MM-DD."}), 400

    return jsonify(
        {
            "status": "success",
            "message": "Saved just now",
            "newly_unlocked": newly_unlocked,
        }
    ), 200


@app.route("/save_log", methods=["POST"])
@login_required
def save_log():
    data = request.get_json(silent=True) or {}
    date_str = data.get("date")

    if not date_str:
        return jsonify({"error": "Date required"}), 400

    _, _, newly_unlocked = _save_daily_log(date_str, data, record_history=True)
    return jsonify(
        {
            "status": "success",
            "message": f"Log for {date_str} saved.",
            "newly_unlocked": newly_unlocked,
        }
    )


@app.route("/load_log/<date_str>")
@login_required
def load_log(date_str):
    log_date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
    # Scope to user
    log = DailyLog.query.filter_by(
        log_date=log_date_obj, user_id=current_user.id
    ).first()

    if log:
        return jsonify(
            {
                "status": "found",
                "tasks": log.completed_tasks or {},
                "notes": log.notes or "",
            }
        )
    return jsonify({"status": "not found"})


@app.route("/get_completed_htb")
@login_required
def get_completed_htb():
    items = (
        TopicHistory.query.filter_by(topic="htb", user_id=current_user.id)
        .order_by(TopicHistory.created_at.desc())
        .all()
    )
    completed_list = [item.entry for item in items]
    return jsonify({"completed": completed_list})


@app.route("/get_completed_bandit")
@login_required
def get_completed_bandit():
    items = (
        TopicHistory.query.filter_by(topic="bandit", user_id=current_user.id)
        .order_by(TopicHistory.created_at.desc())
        .all()
    )
    completed_list = [item.entry for item in items]
    return jsonify({"completed": completed_list})


@app.route("/analytics_data")
@login_required
def analytics_data():
    # Fetch logs ONLY for current user
    streak_summary = _calculate_streak_summary(current_user.id)
    logs = streak_summary["logs"]
    longest_streak = streak_summary["longest_streak"]
    current_streak = streak_summary["current_streak"]
    badge = get_badge(current_streak)
    milestone = milestone_label(current_streak)

    if not logs:
        return jsonify(
            {
                "dates": [],
                "dailyLogs": [],
                "activityByDate": {},
                "topicCounts": {},
                "longestStreak": longest_streak,
                "currentStreak": current_streak,
                "badge_tier": badge["key"],
                "badge_emoji": badge["emoji"],
                "badge_name": badge["name"],
                "milestone_label": milestone,
                "thisMonth": 0,
            }
        )

    dates = [log.log_date.strftime("%Y-%m-%d") for log in logs]
    topic_counts = {}
    activity_by_date = {}

    # Calculate strict date range for "This Month"
    today = date.today()
    start_of_month = today.replace(day=1)
    if today.month == 12:
        start_of_next_month = today.replace(year=today.year + 1, month=1, day=1)
    else:
        start_of_next_month = today.replace(month=today.month + 1, day=1)

    # DEBUG LOGGING (Requested by user)
    app.logger.info("--- Analytics Debug ---")
    app.logger.info(f"today: {today}")
    app.logger.info(f"start_of_month: {start_of_month}")
    app.logger.info(f"start_of_next_month: {start_of_next_month}")
    app.logger.info(f"All active dates: {dates}")

    this_month_count = 0

    for log in logs:
        task_count = 0
        # Count topics
        for key, task_obj in log.completed_tasks.items():
            task = task_obj.get("task") if isinstance(task_obj, dict) else task_obj
            if task:
                topic_counts[key] = topic_counts.get(key, 0) + 1
                task_count += 1

        activity_by_date[log.log_date.strftime("%Y-%m-%d")] = task_count

        # Count this month's logs using strict date range
        if start_of_month <= log.log_date < start_of_next_month:
            this_month_count += 1

    app.logger.info(f"Final this_month_count: {this_month_count}")
    app.logger.info("--- End Debug ---")

    return jsonify(
        {
            "dates": dates,
            "dailyLogs": [1] * len(dates),
            "activityByDate": activity_by_date,
            "topicCounts": topic_counts,
            "longestStreak": longest_streak,
            "currentStreak": current_streak,
            "badge_tier": badge["key"],
            "badge_emoji": badge["emoji"],
            "badge_name": badge["name"],
            "milestone_label": milestone,
            "thisMonth": this_month_count,
        }
    )


if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=5000)
