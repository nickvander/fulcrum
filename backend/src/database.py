"""
Database configuration and session management for the application.

This module sets up the SQLAlchemy engine and session factory, and provides
a dependency for FastAPI to inject database sessions into API endpoints.
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from .config import settings

# The database engine is the entry point to the database.
# It's configured with the URL from the application settings.
engine = create_engine(settings.DATABASE_URL)

# SessionLocal is a factory for creating new database sessions.
# These sessions are the primary interface for database operations.
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    """
    FastAPI dependency to provide a database session to API endpoints.

    This function creates a new session for each request, handles closing
    the session when the request is finished, and ensures that the session

    is always available in a predictable way.

    Yields:
        Session: The SQLAlchemy database session.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
