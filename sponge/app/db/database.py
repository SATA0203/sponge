"""
SQLAlchemy database configuration and session management with connection pooling
"""

from sqlalchemy import create_engine, event
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.pool import QueuePool
from app.core.config import settings
from loguru import logger
import time

# Create database URL
DATABASE_URL = settings.DATABASE_URL or "sqlite:///./sponge.db"

# Override to use SQLite if psycopg2 is not available (for development)
try:
    import psycopg2
except ImportError:
    if DATABASE_URL.startswith("postgresql"):
        logger.warning("psycopg2 not available, falling back to SQLite")
        DATABASE_URL = "sqlite:///./sponge.db"

# Configure engine with connection pooling
if DATABASE_URL.startswith("sqlite"):
    # SQLite doesn't support connection pooling in the same way
    # Use StaticPool for better concurrency
    from sqlalchemy.pool import StaticPool
    
    engine = create_engine(
        DATABASE_URL,
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
        echo=settings.DB_ECHO,
    )
    logger.info("Using SQLite with StaticPool")
else:
    # PostgreSQL/MySQL with connection pooling
    engine = create_engine(
        DATABASE_URL,
        poolclass=QueuePool,
        pool_size=settings.DB_POOL_SIZE,
        max_overflow=20,  # Allow up to 30 connections total
        pool_timeout=30,
        pool_recycle=1800,  # Recycle connections after 30 minutes
        pool_pre_ping=True,  # Verify connections before use
        echo=settings.DB_ECHO,
    )
    logger.info(f"Using PostgreSQL/MySQL with QueuePool (size={settings.DB_POOL_SIZE})")

# Session factory with thread-local scope for better concurrency
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
db_session = scoped_session(SessionLocal)

# Base class for models
Base = declarative_base()
Base.query = db_session.query_property()


def get_db():
    """Dependency for getting database session in FastAPI routes"""
    db = db_session()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Initialize database tables"""
    logger.info("Initializing database tables...")
    Base.metadata.create_all(bind=engine)
    logger.info("Database initialization completed")


def dispose_engine():
    """Dispose of the engine and all connections (useful for shutdown)"""
    logger.info("Disposing database engine...")
    engine.dispose()
    logger.info("Database engine disposed")


# Connection monitoring
@event.listens_for(engine, "connect")
def on_connect(dbapi_connection, connection_record):
    """Log new connections"""
    logger.debug(f"New database connection established: {connection_record}")


@event.listens_for(engine, "checkout")
def on_checkout(dbapi_connection, connection_record, connection_proxy):
    """Log connection checkout and measure wait time"""
    start_time = time.time()
    connection_record.info['checkout_time'] = start_time


@event.listens_for(engine, "checkin")
def on_checkin(dbapi_connection, connection_record):
    """Log connection checkin and measure usage time"""
    checkout_time = connection_record.info.get('checkout_time')
    if checkout_time:
        usage_time = time.time() - checkout_time
        logger.debug(f"Connection used for {usage_time:.3f}s")
