# fix_database.py
from app import app
from database import db
from sqlalchemy import inspect, text

with app.app_context():
    # Create all tables if they don't exist
    db.create_all()
    print("✓ Tables created/verified")
    
    # Check and add missing columns
    inspector = inspect(db.engine)
    columns = [col['name'] for col in inspector.get_columns('sleep_log')]
    
    print("Current columns in sleep_log:", columns)
    
    # Add missing columns
    with db.engine.connect() as conn:
        if 'sleep_latency' not in columns:
            print("Adding sleep_latency column...")
            conn.execute(text("ALTER TABLE sleep_log ADD COLUMN sleep_latency INTEGER DEFAULT 15"))
            print("✓ Added sleep_latency")
        
        if 'wake_after_sleep_onset' not in columns:
            print("Adding wake_after_sleep_onset column...")
            conn.execute(text("ALTER TABLE sleep_log ADD COLUMN wake_after_sleep_onset INTEGER DEFAULT 0"))
            print("✓ Added wake_after_sleep_onset")
        
        conn.commit()
    
    # Verify the fix
    inspector = inspect(db.engine)
    updated_columns = [col['name'] for col in inspector.get_columns('sleep_log')]
    print("\n✅ Updated columns:", updated_columns)
    
    # Show database location
    db_path = db.engine.url.database
    print(f"\n📁 Database location: {db_path}")

print("\n✅ Database fix complete! Restart your app now.")