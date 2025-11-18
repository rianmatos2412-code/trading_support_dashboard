"""
Database connection and session management
"""
import os
from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import NullPool
import logging

logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://trading_user:trading_pass@localhost:5432/trading_db")

# Create engine with connection pooling
engine = create_engine(
    DATABASE_URL,
    poolclass=NullPool,  # TimescaleDB works better without connection pooling in some cases
    pool_pre_ping=True,
    echo=False
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """
    Dependency for getting database session
    """
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        logger.error(f"Database session error: {e}")
        db.rollback()
        raise
    finally:
        db.close()


def init_db():
    """
    Initialize database connection
    """
    try:
        # Test connection
        with engine.connect() as conn:
            conn.execute("SELECT 1")
        logger.info("Database connection established")
        return True
    except Exception as e:
        logger.error(f"Failed to connect to database: {e}")
        return False

