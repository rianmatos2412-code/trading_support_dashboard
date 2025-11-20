"""
Database connection and session management
"""
import os
from typing import Generator, Optional
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool
import logging

logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://trading_user:trading_pass@localhost:5432/trading_db")

# Create engine with connection pooling
engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    pool_recycle=3600,  # Recycle connections after 1 hour
    echo=False
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class DatabaseManager:
    """Context manager for database session management
    
    Provides automatic rollback on exceptions and cleanup.
    Commits should be called explicitly by the calling code.
    """
    
    def __init__(self):
        self._session: Optional[Session] = None
    
    def __enter__(self) -> Session:
        self._session = SessionLocal()
        return self._session
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._session:
            if exc_type is not None:
                # Rollback on exception
                try:
                    self._session.rollback()
                except Exception as e:
                    logger.error(f"Error rolling back session: {e}")
            # Close session (commits should be called explicitly by the code)
            try:
                self._session.close()
            except Exception as e:
                logger.error(f"Error closing session: {e}")
        return False  # Don't suppress exceptions


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
            conn.execute(text("SELECT 1"))
        logger.info("Database connection established")
        return True
    except Exception as e:
        logger.error(f"Failed to connect to database: {e}")
        return False

