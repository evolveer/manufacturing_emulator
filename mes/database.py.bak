"""
MES Emulator - Database Connection
Provides database connection and session management for the MES emulator
"""
import os
import yaml
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.ext.declarative import declarative_base

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

def get_db_session():
    """Get a database session"""
    return Session()

def close_db_session(session):
    """Close a database session"""
    session.close()
