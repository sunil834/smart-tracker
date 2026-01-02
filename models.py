from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from sqlalchemy.dialects.postgresql import JSON
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    logs = db.relationship('DailyLog', backref='author', lazy=True)
    history = db.relationship('TopicHistory', backref='author', lazy=True)
    progress = db.relationship('UserProgress', backref='author', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class DailyLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    log_date = db.Column(db.Date, nullable=False, index=True)
    notes = db.Column(db.Text, nullable=True)
    completed_tasks = db.Column(JSON)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    __table_args__ = (db.UniqueConstraint('user_id', 'log_date', name='_user_date_uc'),)

class TopicHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    topic = db.Column(db.String(100), nullable=False, index=True)
    entry = db.Column(db.String(500), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

class UserProgress(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    room_id = db.Column(db.String(100), nullable=False, index=True)
    completed = db.Column(db.Boolean, default=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    __table_args__ = (db.UniqueConstraint('user_id', 'room_id', name='_user_room_uc'),)