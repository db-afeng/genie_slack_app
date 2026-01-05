"""Database connection management for Databricks Lakebase."""
import os
from urllib.parse import quote_plus
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from databricks.sdk import WorkspaceClient

# Global workspace client and session maker
w = WorkspaceClient()
_engine = None
_SessionLocal = None


def get_lakebase_connection_string():
    """
    Get the Databricks Lakebase PostgreSQL connection string.
    
    In production, Databricks automatically populates these environment variables:
    - PGHOST: Database host
    - PGUSER: Service Principal Client ID
    - PGDATABASE: Database name
    - PGPORT: Database port (default: 5432)
    - PGSSLMODE: SSL mode (default: require)
    
    The OAuth token is retrieved from the Databricks SDK and used as the password.
    
    Returns:
        str: SQLAlchemy connection string for Lakebase (PostgreSQL)
    """
    # Get connection details from environment variables
    host = os.getenv("PGHOST")
    username = os.getenv("PGUSER")
    database = os.getenv("PGDATABASE")
    port = os.getenv("PGPORT", "5432")
    sslmode = os.getenv("PGSSLMODE", "require")
    
    # Validate required environment variables
    required_vars = {
        "PGHOST": host,
        "PGUSER": username,
        "PGDATABASE": database
    }
    
    missing_vars = [var for var, value in required_vars.items() if not value]
    if missing_vars:
        raise ValueError(
            f"Missing required environment variables: {', '.join(missing_vars)}. "
            "These should be automatically set by Databricks in production, "
            "or manually set for local development."
        )
    
    # Get OAuth token from Databricks SDK
    token = w.config.oauth_token().access_token
    
    # URL encode the username and token in case they contain special characters
    username_encoded = quote_plus(username)
    token_encoded = quote_plus(token)
    
    # Construct the PostgreSQL connection string with OAuth token as password
    connection_string = f"postgresql://{username_encoded}:{token_encoded}@{host}:{port}/{database}?sslmode={sslmode}"

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
