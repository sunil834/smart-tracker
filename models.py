from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy import func
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    logs = db.relationship("DailyLog", backref="author", lazy=True)
    history = db.relationship("TopicHistory", backref="author", lazy=True)
    progress = db.relationship("UserProgress", backref="author", lazy=True)
    goals = db.relationship("Goal", backref="author", lazy=True)
    # User-created topics (customizable)
    topics = db.relationship("Topic", backref="owner", lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class DailyLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    log_date = db.Column(db.Date, nullable=False, index=True)
    notes = db.Column(db.Text, nullable=True)
    completed_tasks = db.Column(JSON)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)

    __table_args__ = (db.UniqueConstraint("user_id", "log_date", name="_user_date_uc"),)


class TopicHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    topic = db.Column(db.String(100), nullable=False, index=True)
    # Optional FK to Topic for structured topics
    topic_id = db.Column(
        db.Integer, db.ForeignKey("topic.id"), nullable=True, index=True
    )
    entry = db.Column(db.String(500), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    # Use a dedicated timestamp for reliable chronological ordering
    created_at = db.Column(
        db.DateTime, server_default=func.now(), nullable=False, index=True
    )


class UserProgress(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    room_id = db.Column(db.String(100), nullable=False, index=True)
    completed = db.Column(db.Boolean, default=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)

    __table_args__ = (db.UniqueConstraint("user_id", "room_id", name="_user_room_uc"),)


class Topic(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    goals = db.relationship("Goal", backref="topic", lazy=True)

    __table_args__ = (db.UniqueConstraint("user_id", "name", name="_user_topic_uc"),)


class Goal(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("user.id"), nullable=False, index=True
    )
    topic_id = db.Column(
        db.Integer, db.ForeignKey("topic.id"), nullable=False, index=True
    )
    target_count = db.Column(db.Integer, nullable=False)
    period = db.Column(db.String(10), nullable=False)
    start_date = db.Column(db.Date, nullable=False, server_default=func.current_date())


class Badge(db.Model):
    __tablename__ = "badge"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    tier = db.Column(db.String(32), nullable=False)
    earned_at = db.Column(db.DateTime, default=db.func.now())
