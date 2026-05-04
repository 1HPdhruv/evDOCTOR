"""
==========================================================================
  DATABASE CONFIGURATION & SESSION MANAGEMENT
  --------------------------------------------------------------------------
  This module sets up the SQLAlchemy engine, session factory, and base class
  for the evDOCTOR application. It uses SQLite for local development but
  can be easily switched to PostgreSQL for production (e.g., on Render).

  DBMS Concepts Demonstrated:
    - Database Engine Creation (Connection Pooling)
    - Session Management (Unit of Work Pattern)
    - Declarative Base (ORM Mapping Foundation)
    - Generator-based Dependency Injection for FastAPI
==========================================================================
"""

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, declarative_base
import os
from dotenv import load_dotenv  
load_dotenv(override=False)                    

from sqlalchemy import create_engine, event
...
# ---------------------------------------------------------------------------
# DATABASE URL CONFIGURATION
# ---------------------------------------------------------------------------
# Uses environment variable DATABASE_URL for production (Render PostgreSQL).
# Falls back to local SQLite for development.
# ---------------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    f"sqlite:///{os.path.join(BASE_DIR, 'evdoctor.db')}"
)

# ---------------------------------------------------------------------------
# Fix for Render PostgreSQL: Render gives "postgres://" but SQLAlchemy
# requires "postgresql://"
# ---------------------------------------------------------------------------
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# ---------------------------------------------------------------------------
# ENGINE CREATION
# ---------------------------------------------------------------------------
# The engine is the starting point for any SQLAlchemy application.
# It manages a pool of database connections.
#   - pool_pre_ping=True: Tests connections before use (handles stale conns)
#   - check_same_thread=False: Required for SQLite only (allows multi-thread)
# ---------------------------------------------------------------------------
connect_args = {}
if "sqlite" in DATABASE_URL:
    connect_args["check_same_thread"] = False

engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    pool_pre_ping=True,  # DBMS Concept: Connection health check before use
)

# ---------------------------------------------------------------------------
# ENABLE FOREIGN KEY ENFORCEMENT FOR SQLITE
# ---------------------------------------------------------------------------
# SQLite does NOT enforce foreign keys by default. We must explicitly
# enable it via a PRAGMA command on every new connection.
# This is a critical DBMS concept: Referential Integrity.
# ---------------------------------------------------------------------------
if "sqlite" in DATABASE_URL:
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        """Enable foreign key constraint enforcement in SQLite."""
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

# ---------------------------------------------------------------------------
# SESSION FACTORY
# ---------------------------------------------------------------------------
# Sessions represent a "holding zone" for all objects loaded or associated
# with it during its lifespan. They implement the Unit of Work pattern.
#   - autocommit=False: Explicit transaction control (BEGIN/COMMIT/ROLLBACK)
#   - autoflush=False:  Manual flush control for performance
# ---------------------------------------------------------------------------
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

# ---------------------------------------------------------------------------
# DECLARATIVE BASE
# ---------------------------------------------------------------------------
# All ORM model classes will inherit from this Base. It maintains a catalog
# of classes and tables relative to the Base (the MetaData registry).
# ---------------------------------------------------------------------------
Base = declarative_base()


def get_db():
    """
    Dependency Injection generator for FastAPI.

    DBMS Concept: Session Lifecycle Management
    -------------------------------------------
    - Creates a new database session for each request.
    - Yields the session to the route handler.
    - Ensures the session is closed after the request completes,
      even if an exception occurs (finally block).

    This pattern prevents connection leaks and ensures proper
    transaction boundaries per HTTP request.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
