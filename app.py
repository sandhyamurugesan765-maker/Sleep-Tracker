from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import matplotlib
matplotlib.use('Agg')  # Must be before importing pyplot
import matplotlib.pyplot as plt
import io
import base64
import math
from database import db, User, SleepLog, LifestyleLog, SleepRecommendation
import json
from datetime import datetime, time, timedelta, date, timezone
import os
import logging
from sqlalchemy import text
import sys
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Secret key
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', os.urandom(24).hex())

# Database configuration
database_url = os.environ.get('DATABASE_URL')
if database_url:
    # Fix for postgres:// vs postgresql://
    if database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
    print("✅ Using PostgreSQL database")
else:
    # Fallback to SQLite for local development without Docker
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///sleep_tracker.db'
    print("⚠️ Using SQLite database (local fallback)")

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_recycle': 300,
    'pool_pre_ping': True,
}

# Configure logging FIRST
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create Flask app FIRST
app = Flask(__name__)

# Production configuration
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', os.urandom(24).hex())

# Database configuration for Render PostgreSQL
database_url = os.environ.get('DATABASE_URL')
if database_url:
    # Render provides DATABASE_URL, fix for SQLAlchemy 1.4+
    if database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
    logger.info(f"✅ Using PostgreSQL database")
    
    # Force PostgreSQL dialect
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        'pool_recycle': 300,
        'pool_pre_ping': True,
        'echo': False,  # Set to True only for debugging
    }
else:
    # Fallback to SQLite for local development
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///sleep_tracker.db'
    logger.warning("⚠️ DATABASE_URL not found, using SQLite (local development only)")
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {}

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize extensions AFTER app is configured
db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access this page.'

# Database initialization function
def init_database():
    with app.app_context():
        try:
            # Check if we're using PostgreSQL or SQLite
            db_engine = app.config['SQLALCHEMY_DATABASE_URI']
            logger.info(f"Using database: {db_engine.split('://')[0]}")
            
            # Create all tables
            db.create_all()
            logger.info("✅ Database tables created/verified successfully")
            
            # Verify tables exist
            from sqlalchemy import inspect
            inspector = inspect(db.engine)
            tables = inspector.get_table_names()
            logger.info(f"Tables in database: {tables}")
            
        except Exception as e:
            logger.error(f"❌ Database initialization failed: {e}")
            # Don't exit in production, let the app try to recover
            if 'DATABASE_URL' not in os.environ:
                logger.error("This might be because you're using SQLite locally. If deploying to Render, make sure DATABASE_URL is set.")

# Call it before the first request - SINGLE before_request handler
@app.before_request
def before_first_request():
    if not hasattr(app, 'database_initialized'):
        init_database()
        app.database_initialized = True

@login_manager.user_loader
def load_user(user_id):
    try:
        return db.session.get(User, int(user_id))
    except Exception as e:
        logger.error(f"Error loading user: {e}")
        return None

# Custom Jinja2 filters
@app.template_filter('clamp')
def clamp_filter(value, min_val, max_val):
    try:
        return max(min_val, min(float(value), max_val))
    except (ValueError, TypeError):
        return value

# Context processor for template helpers
@app.context_processor
def utility_processor():
    def calculate_time_in_bed_template(bedtime, wake_up):
        if not bedtime or not wake_up:
            return 0
        bedtime_dt = datetime.combine(date.today(), bedtime)
        wakeup_dt = datetime.combine(date.today(), wake_up)
        
        if wakeup_dt < bedtime_dt:
            wakeup_dt += timedelta(days=1)
        
        return round((wakeup_dt - bedtime_dt).total_seconds() / 3600, 1)
    
    return dict(calculate_time_in_bed=calculate_time_in_bed_template)

# Helper function for calculating time in bed
def calculate_time_in_bed(bedtime, wake_up):
    bedtime_dt = datetime.combine(datetime.today(), bedtime)
    wakeup_dt = datetime.combine(datetime.today(), wake_up)
    
    if wakeup_dt < bedtime_dt:
        wakeup_dt += timedelta(days=1)
    
    return (wakeup_dt - bedtime_dt).total_seconds() / 3600

# Health check endpoint for Render
@app.route('/health')
def health():
    try:
        # Test database connection
        db.session.execute(text('SELECT 1'))
        return jsonify({'status': 'healthy', 'database': 'connected'}), 200
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return jsonify({'status': 'unhealthy', 'error': str(e)}), 500

# ========== ALL YOUR EXISTING ROUTES GO HERE ==========
# Copy ALL your route functions exactly as you had them:
# profile(), sleep_log(), analysis(), lifestyle(), 
# generate_sleep_recommendations(), generate_lifestyle_recommendations(),
# reports(), dashboard(), register(), login(), logout(), index(),
# complete_recommendation(), api_sleep_data()

# Module 1: User Profile Module
@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        current_user.age = request.form.get('age', type=int)
        current_user.lifestyle = request.form.get('lifestyle')
        current_user.sleep_goal = request.form.get('sleep_goal', type=int)
        db.session.commit()
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('profile'))
    
    # Calculate statistics for the profile page
    total_sleep_logs = SleepLog.query.filter_by(user_id=current_user.id).count()
    
    # Calculate average sleep duration
    sleep_logs = SleepLog.query.filter_by(user_id=current_user.id).all()
    avg_sleep_duration = 0
    if sleep_logs:
        total_duration = sum([log.sleep_duration or 0 for log in sleep_logs])
        avg_sleep_duration = total_duration / len(sleep_logs)
    
    # Calculate consistency score (simplified)
    consistency_score = 0
    if len(sleep_logs) > 1:
        durations = [log.sleep_duration or 0 for log in sleep_logs if log.sleep_duration]
        if durations:
            avg_duration = sum(durations) / len(durations)
            variances = [abs(d - avg_duration) for d in durations]
            max_variance = max(variances) if variances else 1
            consistency_score = max(0, 100 - (sum(variances) / len(variances) / max_variance * 100))
    
    return render_template('profile.html',
                         total_sleep_logs=total_sleep_logs,
                         avg_sleep_duration=avg_sleep_duration,
                         consistency_score=consistency_score)

# Module 2: Sleep Logging Module
@app.route('/sleep_log', methods=['GET', 'POST'])
@login_required
def sleep_log():
    if request.method == 'POST':
        try:
            date_str = request.form['date']
            bedtime_str = request.form['bedtime']
            wakeup_str = request.form['wake_up_time']
            
            date_val = datetime.strptime(date_str, '%Y-%m-%d').date()
            bedtime = datetime.strptime(bedtime_str, '%H:%M').time()
            wake_up = datetime.strptime(wakeup_str, '%H:%M').time()
            
            # Get the new fields
            sleep_latency = request.form.get('sleep_latency', 15, type=int)  # minutes
            wake_after_sleep_onset = request.form.get('wake_after_sleep_onset', 0, type=int)  # minutes
            
            # Calculate total time in bed
            bedtime_dt = datetime.combine(date_val, bedtime)
            wakeup_dt = datetime.combine(date_val, wake_up)
            
            if wakeup_dt < bedtime_dt:
                wakeup_dt += timedelta(days=1)
            
            time_in_bed_hours = (wakeup_dt - bedtime_dt).total_seconds() / 3600
            
            # Calculate actual sleep time (convert minutes to hours)
            sleep_latency_hours = sleep_latency / 60
            waso_hours = wake_after_sleep_onset / 60
            actual_sleep_hours = max(0, time_in_bed_hours - sleep_latency_hours - waso_hours)
            
            # Calculate sleep efficiency
            sleep_efficiency = (actual_sleep_hours / time_in_bed_hours * 100) if time_in_bed_hours > 0 else 0
            sleep_efficiency = max(0, min(100, sleep_efficiency))  # Clamp between 0-100
            
            # Create sleep log with corrected values
            sleep_log_entry = SleepLog(
                user_id=current_user.id,
                date=date_val,
                bedtime=bedtime,
                wake_up_time=wake_up,
                nap_duration=request.form.get('nap_duration', 0, type=int),
                sleep_latency=sleep_latency,  # Store in minutes
                wake_after_sleep_onset=wake_after_sleep_onset,  # Store in minutes
                sleep_quality=request.form.get('sleep_quality', type=int),
                notes=request.form.get('notes', ''),
                sleep_duration=actual_sleep_hours,  # Store actual sleep time in hours
                sleep_efficiency=sleep_efficiency
            )
            
            db.session.add(sleep_log_entry)
            db.session.commit()
            
            # Generate recommendations
            generate_sleep_recommendations(current_user.id)
            
            flash('Sleep log saved successfully!', 'success')
            return redirect(url_for('dashboard'))
            
        except Exception as e:
            flash(f'Error saving sleep log: {str(e)}', 'error')
    
    # Get recent sleep logs for display
    recent_logs = SleepLog.query.filter_by(
        user_id=current_user.id
    ).order_by(SleepLog.date.desc()).limit(5).all()
    
    return render_template('sleep_log.html', 
                         recent_logs=recent_logs,
                         now=datetime.now(timezone.utc))

# Module 3: Sleep Quality Analysis Module
@app.route('/analysis')
@login_required
def analysis():
    # Get sleep logs from last 7 days
    end_date = datetime.now(timezone.utc).date()
    start_date = end_date - timedelta(days=7)
    
    sleep_logs = SleepLog.query.filter(
        SleepLog.user_id == current_user.id,
        SleepLog.date >= start_date,
        SleepLog.date <= end_date
    ).order_by(SleepLog.date).all()
    
    # Calculate sleep efficiency for each log
    for log in sleep_logs:
        if log.sleep_duration:
            time_in_bed = calculate_time_in_bed(log.bedtime, log.wake_up_time)
            if time_in_bed > 0:
                log.sleep_efficiency = (log.sleep_duration / time_in_bed) * 100
            else:
                log.sleep_efficiency = 0
    
    # Prepare data for visualization
    dates = [log.date.strftime('%m-%d') for log in sleep_logs]
    durations = [log.sleep_duration or 0 for log in sleep_logs]
    qualities = [log.sleep_quality or 0 for log in sleep_logs]
    efficiencies = [log.sleep_efficiency or 0 for log in sleep_logs]
    
    # Calculate averages
    avg_duration = sum(durations) / len(durations) if durations else 0
    avg_quality = sum(qualities) / len(qualities) if qualities else 0
    avg_efficiency = sum(efficiencies) / len(efficiencies) if efficiencies else 0
    
    # Generate sleep efficiency chart
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.plot(dates, durations, marker='o', label='Duration (hrs)')
    ax.plot(dates, qualities, marker='s', label='Quality (1-10)')
    ax.plot(dates, efficiencies, marker='^', label='Efficiency (%)')
    ax.set_xlabel('Date')
    ax.set_ylabel('Metrics')
    ax.set_title('Sleep Analysis - Last 7 Days')
    ax.legend()
    ax.grid(True, alpha=0.3)
    
    img = io.BytesIO()
    plt.tight_layout()
    plt.savefig(img, format='png')
    img.seek(0)
    chart_url = base64.b64encode(img.getvalue()).decode()
    plt.close()
    
    return render_template('analysis.html',
                         sleep_logs=sleep_logs,
                         avg_duration=avg_duration,
                         avg_quality=avg_quality,
                         avg_efficiency=avg_efficiency,
                         chart_url=chart_url)

# Module 4: Lifestyle Factor Module
@app.route('/lifestyle', methods=['GET', 'POST'])
@login_required
def lifestyle():
    if request.method == 'POST':
        try:
            lifestyle_log = LifestyleLog(
                user_id=current_user.id,
                date=datetime.now(timezone.utc).date(),
                caffeine_intake=request.form.get('caffeine_intake', 0, type=int),
                screen_time=request.form.get('screen_time', 0, type=int),
                exercise_duration=request.form.get('exercise_duration', 0, type=int),
                exercise_time=request.form.get('exercise_time'),
                stress_level=request.form.get('stress_level', 5, type=int),
                alcohol_intake=request.form.get('alcohol_intake', 0, type=int),
                meal_time=datetime.strptime(request.form['meal_time'], '%H:%M').time() if request.form.get('meal_time') else None
            )
            
            db.session.add(lifestyle_log)
            db.session.commit()
            
            # Generate recommendations based on lifestyle
            generate_lifestyle_recommendations(current_user.id, lifestyle_log)
            
            flash('Lifestyle data saved successfully!', 'success')
            return redirect(url_for('dashboard'))
            
        except Exception as e:
            flash(f'Error saving lifestyle data: {str(e)}', 'error')
    
    # Get recent lifestyle logs
    recent_logs = LifestyleLog.query.filter_by(
        user_id=current_user.id
    ).order_by(LifestyleLog.date.desc()).limit(5).all()
    
    return render_template('lifestyle.html', recent_logs=recent_logs)

# Module 5: Sleep Recommendation Module (Rule-based)
def generate_sleep_recommendations(user_id):
    # Get last 3 sleep logs
    sleep_logs = SleepLog.query.filter_by(
        user_id=user_id
    ).order_by(SleepLog.date.desc()).limit(3).all()
    
    if not sleep_logs:
        return
    
    latest_log = sleep_logs[0]
    user = db.session.get(User, user_id)
    
    recommendations = []
    
    # Rule 1: Sleep duration recommendations
    if latest_log.sleep_duration:
        if latest_log.sleep_duration < 6:
            recommendations.append({
                'type': 'sleep_duration',
                'message': 'Your sleep duration is less than 6 hours. Try to maintain at least 7-8 hours of sleep.',
                'priority': 3
            })
        elif latest_log.sleep_duration > 9:
            recommendations.append({
                'type': 'sleep_duration',
                'message': 'You\'re sleeping more than 9 hours. Consider if you\'re getting enough quality sleep.',
                'priority': 2
            })
    
    # Rule 2: Consistency recommendations
    if len(sleep_logs) >= 3:
        durations = [log.sleep_duration for log in sleep_logs if log.sleep_duration]
        if durations:
            variance = max(durations) - min(durations)
            if variance > 2:
                recommendations.append({
                    'type': 'consistency',
                    'message': 'Your sleep schedule varies significantly. Try to maintain consistent bedtimes.',
                    'priority': 2
                })
    
    # Rule 3: Sleep quality recommendations
    if latest_log.sleep_quality and latest_log.sleep_quality < 6:
        recommendations.append({
            'type': 'sleep_quality',
            'message': 'Your sleep quality is low. Consider improving your sleep environment.',
            'priority': 2
        })
    
    # Save recommendations to database
    for rec in recommendations:
        recommendation = SleepRecommendation(
            user_id=user_id,
            date=datetime.now(timezone.utc).date(),
            recommendation_type=rec['type'],
            message=rec['message'],
            priority=rec['priority']
        )
        db.session.add(recommendation)
    
    db.session.commit()

def generate_lifestyle_recommendations(user_id, lifestyle_log):
    recommendations = []
    
    # Rule 1: Caffeine intake
    if lifestyle_log.caffeine_intake > 200:
        recommendations.append({
            'type': 'caffeine',
            'message': f'Your caffeine intake ({lifestyle_log.caffeine_intake}mg) is high. Limit to 200mg or less, especially after 2 PM.',
            'priority': 2
        })
    
    # Rule 2: Screen time before bed
    if lifestyle_log.screen_time > 60:
        recommendations.append({
            'type': 'screen_time',
            'message': f'You had {lifestyle_log.screen_time} minutes of screen time before bed. Try to limit to 30 minutes or use blue light filters.',
            'priority': 3
        })
    
    # Rule 3: Exercise timing
    if lifestyle_log.exercise_time == 'night' and lifestyle_log.exercise_duration > 30:
        recommendations.append({
            'type': 'exercise_timing',
            'message': 'Vigorous exercise close to bedtime can disrupt sleep. Try to exercise earlier in the day.',
            'priority': 2
        })
    
    # Rule 4: Meal timing
    if lifestyle_log.meal_time:
        meal_hour = lifestyle_log.meal_time.hour
        if meal_hour >= 21:  # Eating after 9 PM
            recommendations.append({
                'type': 'meal_timing',
                'message': 'Eating close to bedtime can disrupt sleep. Try to have your last meal 2-3 hours before bed.',
                'priority': 2
            })
    
    # Save recommendations
    for rec in recommendations:
        recommendation = SleepRecommendation(
            user_id=user_id,
            date=datetime.now(timezone.utc).date(),
            recommendation_type=rec['type'],
            message=rec['message'],
            priority=rec['priority']
        )
        db.session.add(recommendation)
    
    db.session.commit()

@app.route('/reports')
@login_required
def reports():
    # Get sleep data for the last 30 days
    end_date = datetime.now(timezone.utc).date()
    start_date = end_date - timedelta(days=30)
    
    sleep_logs = SleepLog.query.filter(
        SleepLog.user_id == current_user.id,
        SleepLog.date >= start_date,
        SleepLog.date <= end_date
    ).order_by(SleepLog.date).all()
    
    lifestyle_logs = LifestyleLog.query.filter(
        LifestyleLog.user_id == current_user.id,
        LifestyleLog.date >= start_date,
        LifestyleLog.date <= end_date
    ).order_by(LifestyleLog.date).all()
    
    # Calculate average sleep efficiency for the period
    avg_efficiency = 0
    if sleep_logs:
        efficiencies = [log.sleep_efficiency for log in sleep_logs if log.sleep_efficiency is not None]
        if efficiencies:
            avg_efficiency = sum(efficiencies) / len(efficiencies)
    
    # Generate monthly trends chart
    if sleep_logs:
        dates = [log.date.strftime('%m-%d') for log in sleep_logs]
        durations = [log.sleep_duration or 0 for log in sleep_logs]
        qualities = [log.sleep_quality or 0 for log in sleep_logs]
        
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10))
        
        # Sleep duration chart
        ax1.bar(dates, durations, color='skyblue', alpha=0.7)
        ax1.axhline(y=current_user.sleep_goal, color='r', linestyle='--', label='Sleep Goal')
        ax1.set_xlabel('Date')
        ax1.set_ylabel('Sleep Duration (hours)')
        ax1.set_title('Sleep Duration - Last 30 Days')
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        plt.setp(ax1.xaxis.get_majorticklabels(), rotation=45)
        
        # Sleep quality chart
        ax2.plot(dates, qualities, marker='o', color='green', linewidth=2)
        ax2.set_xlabel('Date')
        ax2.set_ylabel('Sleep Quality (1-10)')
        ax2.set_title('Sleep Quality - Last 30 Days')
        ax2.grid(True, alpha=0.3)
        plt.setp(ax2.xaxis.get_majorticklabels(), rotation=45)
        
        plt.tight_layout()
        
        img = io.BytesIO()
        plt.savefig(img, format='png')
        img.seek(0)
        monthly_chart = base64.b64encode(img.getvalue()).decode()
        plt.close()
    else:
        monthly_chart = None
    
    # Get recommendations
    recommendations = SleepRecommendation.query.filter_by(
        user_id=current_user.id,
        is_completed=False
    ).order_by(SleepRecommendation.priority.desc()).limit(5).all()
    
    return render_template('reports.html',
                         sleep_logs=sleep_logs,
                         lifestyle_logs=lifestyle_logs,
                         monthly_chart=monthly_chart,
                         recommendations=recommendations,
                         avg_efficiency=avg_efficiency)

# Dashboard
@app.route('/dashboard')
@login_required
def dashboard():
    # Get today's sleep log
    today = datetime.now(timezone.utc).date()
    today_sleep = SleepLog.query.filter_by(
        user_id=current_user.id,
        date=today
    ).first()
    
    # Get sleep logs from last 7 days
    week_ago = today - timedelta(days=7)
    recent_sleep_logs = SleepLog.query.filter(
        SleepLog.user_id == current_user.id,
        SleepLog.date >= week_ago
    ).order_by(SleepLog.date.desc()).all()
    
    # Calculate weekly average
    if recent_sleep_logs:
        avg_duration = sum([log.sleep_duration or 0 for log in recent_sleep_logs]) / len(recent_sleep_logs)
        avg_quality = sum([log.sleep_quality or 0 for log in recent_sleep_logs if log.sleep_quality]) / \
                     len([log for log in recent_sleep_logs if log.sleep_quality]) if recent_sleep_logs else 0
    else:
        avg_duration = 0
        avg_quality = 0
    
    # Get recent recommendations
    recommendations = SleepRecommendation.query.filter_by(
        user_id=current_user.id,
        is_completed=False
    ).order_by(SleepRecommendation.priority.desc()).limit(3).all()
    
    return render_template('dashboard.html',
                         today_sleep=today_sleep,
                         avg_duration=avg_duration,
                         avg_quality=avg_quality,
                         recommendations=recommendations,
                         user=current_user)

# Authentication routes
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        
        if User.query.filter_by(username=username).first():
            flash('Username already exists', 'error')
            return redirect(url_for('register'))
        
        if User.query.filter_by(email=email).first():
            flash('Email already registered', 'error')
            return redirect(url_for('register'))
        
        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
        
        user = User(
            username=username,
            email=email,
            password=hashed_password,
            age=request.form.get('age', type=int),
            lifestyle=request.form.get('lifestyle'),
            sleep_goal=request.form.get('sleep_goal', 8, type=int)
        )
        
        db.session.add(user)
        db.session.commit()
        
        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('dashboard'))
        
        flash('Invalid username or password', 'error')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return render_template('index.html')

@app.route('/complete_recommendation/<int:rec_id>')
@login_required
def complete_recommendation(rec_id):
    recommendation = SleepRecommendation.query.get_or_404(rec_id)
    if recommendation.user_id == current_user.id:
        recommendation.is_completed = True
        db.session.commit()
        flash('Recommendation marked as completed!', 'success')
    return redirect(request.referrer or url_for('dashboard'))

# API endpoints for data
@app.route('/api/sleep_data')
@login_required
def api_sleep_data():
    # Get sleep data for charts
    sleep_logs = SleepLog.query.filter_by(
        user_id=current_user.id
    ).order_by(SleepLog.date).limit(14).all()
    
    data = {
        'dates': [log.date.strftime('%Y-%m-%d') for log in sleep_logs],
        'durations': [log.sleep_duration or 0 for log in sleep_logs],
        'qualities': [log.sleep_quality or 0 for log in sleep_logs]
    }
    
    return jsonify(data)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    
    # Initialize database on startup
    with app.app_context():
        try:
            init_database()
        except Exception as e:
            logger.error(f"Startup database initialization error: {e}")
    
    app.run(host='0.0.0.0', port=port, debug=debug)