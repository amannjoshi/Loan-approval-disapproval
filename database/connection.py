"""
Database Connection Manager
===========================
PostgreSQL connection management using SQLAlchemy.

Supports:
- Connection pooling
- Session management
- Transaction handling
- Health checks

Author: Loan Analytics Team
Version: 1.0.0
"""

import os
import logging
from typing import Optional, Generator
from contextlib import contextmanager

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool
from sqlalchemy.exc import SQLAlchemyError

from .models import Base

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DatabaseConfig:
    """Database configuration from environment variables."""
    
    def __init__(self):
        self.host = os.getenv('DB_HOST', 'localhost')
        self.port = os.getenv('DB_PORT', '5432')
        self.database = os.getenv('DB_NAME', 'loan_approval')
        self.username = os.getenv('DB_USER', 'postgres')
        self.password = os.getenv('DB_PASSWORD', 'postgres')
        self.pool_size = int(os.getenv('DB_POOL_SIZE', '5'))
        self.max_overflow = int(os.getenv('DB_MAX_OVERFLOW', '10'))
        self.echo = os.getenv('DB_ECHO', 'false').lower() == 'true'
    
    @property
    def database_url(self) -> str:
        """Get PostgreSQL connection URL."""
        return f"postgresql://{self.username}:{self.password}@{self.host}:{self.port}/{self.database}"
    
    @property
    def async_database_url(self) -> str:
        """Get async PostgreSQL connection URL."""
        return f"postgresql+asyncpg://{self.username}:{self.password}@{self.host}:{self.port}/{self.database}"


class DatabaseConnection:
    """
    Singleton database connection manager.
    
    Handles connection pooling, session creation, and cleanup.
    """
    
    _instance: Optional['DatabaseConnection'] = None
    _engine = None
    _session_factory = None
    
    def __new__(cls, config: Optional[DatabaseConfig] = None):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, config: Optional[DatabaseConfig] = None):
        if self._initialized:
            return
        
        self.config = config or DatabaseConfig()
        self._create_engine()
        self._initialized = True
    
    def _create_engine(self):
        """Create SQLAlchemy engine with connection pooling."""
        try:
            self._engine = create_engine(
                self.config.database_url,
                poolclass=QueuePool,
                pool_size=self.config.pool_size,
                max_overflow=self.config.max_overflow,
                pool_pre_ping=True,  # Verify connections before use
                pool_recycle=3600,   # Recycle connections after 1 hour
                echo=self.config.echo
            )
            
            self._session_factory = sessionmaker(
                bind=self._engine,
                autocommit=False,
                autoflush=False,
                expire_on_commit=False
            )
            
            logger.info(f"Database engine created: {self.config.host}:{self.config.port}/{self.config.database}")
            
        except Exception as e:
            logger.error(f"Failed to create database engine: {e}")
            raise
    
    @property
    def engine(self):
        """Get the SQLAlchemy engine."""
        return self._engine
    
    def get_session(self) -> Session:
        """Get a new database session."""
        if not self._session_factory:
            raise RuntimeError("Database not initialized")
        return self._session_factory()
    
    @contextmanager
    def session_scope(self) -> Generator[Session, None, None]:
        """
        Context manager for database sessions.
        
        Automatically commits on success, rolls back on error.
        
        Usage:
            with db.session_scope() as session:
                session.add(entity)
        """
        session = self.get_session()
        try:
            yield session
            session.commit()
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Database error: {e}")
            raise
        except Exception as e:
            session.rollback()
            logger.error(f"Unexpected error: {e}")
            raise
        finally:
            session.close()
    
    def create_tables(self):
        """Create all database tables."""
        try:
            Base.metadata.create_all(self._engine)
            logger.info("Database tables created successfully")
        except Exception as e:
            logger.error(f"Failed to create tables: {e}")
            raise
    
    def drop_tables(self):
        """Drop all database tables (use with caution!)."""
        try:
            Base.metadata.drop_all(self._engine)
            logger.info("Database tables dropped")
        except Exception as e:
            logger.error(f"Failed to drop tables: {e}")
            raise
    
    def health_check(self) -> bool:
        """Check database connectivity."""
        try:
            with self._engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return True
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False
    
    def get_connection_stats(self) -> dict:
        """Get connection pool statistics."""
        pool = self._engine.pool
        return {
            'pool_size': pool.size(),
            'checked_in': pool.checkedin(),
            'checked_out': pool.checkedout(),
            'overflow': pool.overflow(),
            'invalid': pool.invalidatedcount() if hasattr(pool, 'invalidatedcount') else 0
        }
    
    def close(self):
        """Close all connections and dispose engine."""
        if self._engine:
            self._engine.dispose()
            logger.info("Database connections closed")


# ============================================================================
# Module-level convenience functions
# ============================================================================

_db_connection: Optional[DatabaseConnection] = None


def init_database(config: Optional[DatabaseConfig] = None) -> DatabaseConnection:
    """
    Initialize the database connection.
    
    Call this at application startup.
    """
    global _db_connection
    _db_connection = DatabaseConnection(config)
    return _db_connection


def get_db() -> DatabaseConnection:
    """Get the database connection instance."""
    global _db_connection
    if _db_connection is None:
        _db_connection = DatabaseConnection()
    return _db_connection


def get_db_session() -> Session:
    """Get a new database session."""
    return get_db().get_session()


@contextmanager
def get_session_context() -> Generator[Session, None, None]:
    """Context manager for database sessions."""
    with get_db().session_scope() as session:
        yield session


def create_all_tables():
    """Create all database tables."""
    get_db().create_tables()


def check_database_health() -> bool:
    """Check if database is accessible."""
    return get_db().health_check()


# ============================================================================
# Database Setup Script
# ============================================================================

def setup_database():
    """
    Complete database setup including creating database if not exists.
    
    Run this script to initialize the database.
    """
    import psycopg2
    from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
    
    config = DatabaseConfig()
    
    # Connect to PostgreSQL server (not specific database)
    try:
        conn = psycopg2.connect(
            host=config.host,
            port=config.port,
            user=config.username,
            password=config.password,
            database='postgres'  # Connect to default database
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        
        # Check if database exists
        cursor.execute(
            "SELECT 1 FROM pg_database WHERE datname = %s",
            (config.database,)
        )
        exists = cursor.fetchone()
        
        if not exists:
            # Create database
            cursor.execute(f'CREATE DATABASE {config.database}')
            logger.info(f"Database '{config.database}' created")
        else:
            logger.info(f"Database '{config.database}' already exists")
        
        cursor.close()
        conn.close()
        
        # Initialize connection and create tables
        db = init_database(config)
        db.create_tables()
        
        logger.info("Database setup completed successfully!")
        return True
        
    except Exception as e:
        logger.error(f"Database setup failed: {e}")
        return False


if __name__ == "__main__":
    # Run setup when executed directly
    print("Setting up Loan Approval Database...")
    print("="*50)
    
    success = setup_database()
    
    if success:
        print("\n✅ Database setup completed!")
        
        # Test connection
        db = get_db()
        if db.health_check():
            print("✅ Database health check passed")
            print(f"   Connection stats: {db.get_connection_stats()}")
        else:
            print("❌ Database health check failed")
    else:
        print("\n❌ Database setup failed!")
        print("   Make sure PostgreSQL is running and credentials are correct.")
