"""
MES Emulator - Database Connection
Provides database connection and session management for the MES emulator
"""
import os
import yaml
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.exc import SQLAlchemyError

# Load configuration
def load_config():
    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config.yaml')
    with open(config_path, 'r') as file:
        return yaml.safe_load(file)

config = load_config()
database_url = config['mes']['database']

# Create engine and session
engine = create_engine(database_url)
session_factory = sessionmaker(bind=engine)
Session = scoped_session(session_factory)

def _ensure_work_order_inventory_column():
    """Add inventory_posted column to work_orders if it is missing (sqlite fallback)."""
    if engine.dialect.name != 'sqlite':
        return
    try:
        with engine.begin() as conn:
            cols = conn.execute(text("PRAGMA table_info('work_orders')")).fetchall()
            col_names = {row[1] for row in cols}  # second column is name
            if 'inventory_posted' not in col_names:
                conn.execute(text("ALTER TABLE work_orders ADD COLUMN inventory_posted BOOLEAN DEFAULT 0"))
    except SQLAlchemyError:
        # Don't crash startup if migration fails; errors will surface on query
        pass

# Ensure compatibility migrations are applied on import
_ensure_work_order_inventory_column()

def get_db_session():
    """Get a database session"""
    return Session()

def close_db_session(session):
    """Close a database session"""
    session.close()
