# Database Module

This module handles database connections to the Databricks Lakebase instance for persistent storage of conversation tracking data.

## Overview

The database module provides a seamless integration between local development (in-memory storage) and production (Lakebase database storage) environments.

## Components

### `connection.py`
Manages the SQLAlchemy connection to the Databricks Lakebase instance:
- `get_lakebase_connection_string()`: Constructs the Databricks connection string
- `get_lakebase_warehouse_id()`: Retrieves the Lakebase warehouse ID by name
- `init_engine()`: Initializes the SQLAlchemy engine
- `get_session()`: Returns a database session for queries
- `get_engine()`: Returns the SQLAlchemy engine

### `models.py`
Defines the database schema:
- `ConversationTracker`: Model for tracking Slack threads to Genie conversation mappings
  - `thread_ts`: Slack thread timestamp (primary key)
  - `conversation_id`: Genie conversation ID
  - `genie_room_id`: Genie room/space ID
  - `genie_room_name`: Genie room/space name
  - `created_at`: Creation timestamp
  - `updated_at`: Last update timestamp

### `conv_tracker.py`
Provides a unified API for conversation tracking that works in both local and production modes:
- `init_database()`: Initialize database tables (production only)
- `get_conversation(thread_ts)`: Retrieve conversation details
- `set_conversation(thread_ts, room_details)`: Create/update conversation
- `update_conversation_id(thread_ts, conversation_id)`: Update conversation ID
- `delete_conversation(thread_ts)`: Delete a conversation
- `clear_all_conversations()`: Clear all conversations (use with caution)

## Environment Modes

### Local Development (`IS_LOCAL=true`)
- Uses in-memory dictionary storage
- No database connection required
- Data is lost when the application restarts

### Production (`IS_LOCAL` not set or `false`)
- Uses Databricks Lakebase for persistent storage
- Automatically creates tables on initialization
- Data persists across application restarts

## Setup

### Dependencies
The following packages are required (already added to `requirements.txt`):
- `SQLAlchemy==2.0.45`
- `psycopg==3.2.3` (PostgreSQL driver)

### Lakebase Configuration

The Lakebase instance is configured in `resources/lakebase.yml`:
```yaml
resources:
  database_instances:
    genie_slack_lakebase:
      name: genie-slack-lakebase
      capacity: CU_1
```

**Connection Details:**

The connection uses PostgreSQL protocol via environment variables:

**Environment Variables (automatically set by Databricks in production):**
- `PGHOST`: Database host
- `PGUSER`: Service Principal Client ID (automatically set to the app's identity)
- `PGDATABASE`: Database name
- `PGPORT`: Database port (default: 5432)
- `PGSSLMODE`: SSL mode (default: require)

**Authentication:**
The connection uses OAuth token authentication retrieved from the Databricks SDK:
```python
token = w.config.oauth_token().access_token
```
This token is automatically managed and rotated by Databricks.

**For Local Development:**
Set these environment variables manually in your `.env` file or shell:
```bash
export PGHOST="instance-15dc10d7-b8c2-4f76-bb9e-c1565eddc6a0.database.azuredatabricks.net"
export PGUSER="your-service-principal-id"
export PGDATABASE="databricks_postgres"
export PGPORT="5432"
export PGSSLMODE="require"
export IS_LOCAL="true"
```
Note: The OAuth token is retrieved automatically from the Databricks SDK, so no manual password configuration is needed.

### Usage in Code
```python
from database.conv_tracker import get_conversation, set_conversation, update_conversation_id

# Set conversation details
set_conversation("thread_123", {
    "genie_room_id": "room_456",
    "genie_room_name": "My Genie Room"
})

# Get conversation details
conv_data = get_conversation("thread_123")
# Returns: {"genie_room_id": "room_456", "genie_room_name": "My Genie Room", "conversation_id": None}

# Update conversation ID after starting a conversation
update_conversation_id("thread_123", "conv_789")
```

## Database Schema

The application uses a dedicated schema `genie_app` to organize its tables separately from other database objects.

**Schema:** `genie_app`

```sql
-- Schema is automatically created if it doesn't exist
CREATE SCHEMA IF NOT EXISTS genie_app;

-- Conversation tracker table
CREATE TABLE genie_app.conversation_tracker (
    thread_ts VARCHAR PRIMARY KEY,
    conversation_id VARCHAR,
    genie_room_id VARCHAR NOT NULL,
    genie_room_name VARCHAR NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

The schema and tables are automatically created when the application starts (in non-local mode) via the `init_database()` function.

## Error Handling

The module includes error handling for:
- Database connection failures
- Lakebase instance not found
- SQL operation errors

All database operations are wrapped in try-catch blocks and will log errors while gracefully degrading functionality.

## Migration from In-Memory Storage

The old `conv_tracker` dictionary has been completely replaced with the new database-backed system. The API is designed to be backward compatible:

**Old code:**
```python
conv_tracker[thread_ts] = room_details
data = conv_tracker.get(thread_ts, {})
conv_tracker[thread_ts]["conversation_id"] = conv_id
```

**New code:**
```python
set_conversation(thread_ts, room_details)
data = get_conversation(thread_ts) or {}
update_conversation_id(thread_ts, conv_id)
```
