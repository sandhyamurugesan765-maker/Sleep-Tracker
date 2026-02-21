from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timezone
from flask_login import UserMixin
import json

db = SQLAlchemy()

def get_utc_now():
    return datetime.now(timezone.utc)

def get_utc_today():
    return datetime.now(timezone.utc).date()

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    age = db.Column(db.Integer)
    lifestyle = db.Column(db.String(50))
    sleep_goal = db.Column(db.Integer, default=8)
    created_at = db.Column(db.DateTime, default=get_utc_now)
    
    sleep_logs = db.relationship('SleepLog', backref='user', lazy=True)
    lifestyle_logs = db.relationship('LifestyleLog', backref='user', lazy=True)

class SleepLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    date = db.Column(db.Date, nullable=False, default=get_utc_today)
    bedtime = db.Column(db.Time, nullable=False)
    wake_up_time = db.Column(db.Time, nullable=False)
    nap_duration = db.Column(db.Integer, default=0)  # minutes
    
    # NEW FIELDS for accurate efficiency calculation
    sleep_latency = db.Column(db.Integer, default=15)  # minutes to fall asleep
    wake_after_sleep_onset = db.Column(db.Integer, default=0)  # minutes awake during night
    
    sleep_quality = db.Column(db.Integer)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=get_utc_now)
    
    sleep_duration = db.Column(db.Float)  # actual sleep time in hours
    sleep_efficiency = db.Column(db.Float)  # percentage

class LifestyleLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    date = db.Column(db.Date, nullable=False, default=get_utc_today)
    caffeine_intake = db.Column(db.Integer, default=0)
    screen_time = db.Column(db.Integer, default=0)
    exercise_duration = db.Column(db.Integer, default=0)
    exercise_time = db.Column(db.String(20))
    stress_level = db.Column(db.Integer, default=5)
    alcohol_intake = db.Column(db.Integer, default=0)
    meal_time = db.Column(db.Time)
    created_at = db.Column(db.DateTime, default=get_utc_now)

class SleepRecommendation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    date = db.Column(db.Date, nullable=False, default=get_utc_today)
    recommendation_type = db.Column(db.String(50))
    message = db.Column(db.Text)
    priority = db.Column(db.Integer, default=1)
    is_completed = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=get_utc_now)