"""Database connection management for Databricks Lakebase."""
import os
from sqlalchemy import create_engine, MetaData
from sqlalchemy.orm import sessionmaker, Session
from databricks.sdk import WorkspaceClient

# Global engine and session maker
_engine = None
_SessionLocal = None


def get_lakebase_connection_string():
    """
    Get the Databricks Lakebase PostgreSQL connection string.
    
    Returns:
        str: SQLAlchemy connection string for Lakebase (PostgreSQL)
    """
    # Lakebase connection details
    username = "alex.feng@databricks.com"
    host = "instance-15dc10d7-b8c2-4f76-bb9e-c1565eddc6a0.database.azuredatabricks.net"
    port = "5432"
    database = "databricks_postgres"
    
    # Get password from environment or secrets
    if os.environ.get("IS_LOCAL") == 'true':
        # For local dev, use environment variable
        password = os.environ.get("PGPASSWORD")
        if not password:
            raise ValueError("PGPASSWORD environment variable not set for local development")
    else:
        # In Databricks, get from secrets
        w = WorkspaceClient()
        password = w.dbutils.secrets.get(scope='genie-slack-secret-scope', key='pgpassword')
    
    # Construct the PostgreSQL connection string
    # URL encode the username (@ -> %40)
    username_encoded = username.replace("@", "%40")
    connection_string = f"postgresql://{username_encoded}:{password}@{host}:{port}/{database}?sslmode=require"
    
    return connection_string


def init_engine():
    """Initialize the SQLAlchemy engine for Lakebase."""
    global _engine, _SessionLocal
    
    if _engine is None:
        connection_string = get_lakebase_connection_string()
        _engine = create_engine(
            connection_string,
            echo=False,  # Set to True for SQL debugging
            future=True,
            pool_pre_ping=True,  # Verify connections before using them
            pool_recycle=3600,  # Recycle connections after 1 hour
        )
        _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_engine)
    
    return _engine


def get_session() -> Session:
    """
    Get a database session.
    
    Returns:
        Session: SQLAlchemy session
    """
    if _SessionLocal is None:
        init_engine()
    
    return _SessionLocal()


def get_engine():
    """
    Get the SQLAlchemy engine.
    
    Returns:
        Engine: SQLAlchemy engine
    """
    if _engine is None:
        init_engine()
    
    return _engine
