"""
EchoTrace Database Configuration
"""

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from contextlib import contextmanager

# Database path
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'database', 'manufacturing.db')
DATABASE_URL = f'sqlite:///{DB_PATH}'

# Create engine
engine = create_engine(
    DATABASE_URL,
    connect_args={'check_same_thread': False},
    echo=False
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Session = scoped_session(SessionLocal)


@contextmanager
def get_db_session():
    """
    Context manager for database sessions
    Ensures proper session cleanup
    """
    session = Session()
    try:
        yield session
        session.commit()
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()


def init_db():
    """Initialize EchoTrace database tables"""
    from echotrace.models import Base
    Base.metadata.create_all(bind=engine)
    print("EchoTrace database tables created successfully")


if __name__ == '__main__':
    init_db()
