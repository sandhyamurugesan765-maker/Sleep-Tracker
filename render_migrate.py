# render_migrate.py
from app import app
from database import db
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

with app.app_context():
    logger.info("Creating database tables...")
    db.create_all()
    logger.info("✅ Tables created successfully!")
    
    # Verify tables exist
    from sqlalchemy import inspect
    inspector = inspect(db.engine)
    tables = inspector.get_table_names()
    logger.info(f"Tables in database: {tables}")