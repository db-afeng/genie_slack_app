"""Conversation tracker operations - handles both in-memory and database storage."""
import os
from typing import Optional, Dict
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from database.connection import get_session, get_engine
from database.models import Base, ConversationTracker, SCHEMA_NAME


# In-memory tracker for local development
_local_conv_tracker = {}


def is_local_mode():
    """Check if running in local development mode."""
    return os.environ.get("IS_LOCAL") == 'true'


def init_database():
    """Initialize the database schema and tables. Only called in non-local mode."""
    if not is_local_mode():
        try:
            engine = get_engine()
            
            # Create the schema if it doesn't exist
            with engine.connect() as conn:
                conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {SCHEMA_NAME}"))
                conn.commit()
                print(f"Schema '{SCHEMA_NAME}' ensured to exist")
            
            # Create all tables in the schema
            Base.metadata.create_all(bind=engine)
            print(f"Database tables initialized successfully in schema '{SCHEMA_NAME}'")
        except Exception as e:
            print(f"Error initializing database: {e}")
            raise


def get_conversation(thread_ts: str) -> Optional[Dict]:
    """
    Get conversation details for a thread.
    
    Args:
        thread_ts: Slack thread timestamp
        
    Returns:
        Dict with conversation details or None if not found
    """
    if is_local_mode():
        return _local_conv_tracker.get(thread_ts)
    else:
        session = get_session()
        try:
            tracker = session.query(ConversationTracker).filter_by(thread_ts=thread_ts).first()
            return tracker.to_dict() if tracker else None
        except SQLAlchemyError as e:
            print(f"Error getting conversation: {e}")
            return None
        finally:
            session.close()


def set_conversation(thread_ts: str, room_details: Dict):
    """
    Set/create conversation details for a thread.
    
    Args:
        thread_ts: Slack thread timestamp
        room_details: Dict with genie_room_id, genie_room_name, and optionally conversation_id
    """
    if is_local_mode():
        _local_conv_tracker[thread_ts] = room_details
    else:
        session = get_session()
        try:
            # Check if exists
            tracker = session.query(ConversationTracker).filter_by(thread_ts=thread_ts).first()
            
            if tracker:
                # Update existing
                tracker.genie_room_id = room_details.get("genie_room_id", tracker.genie_room_id)
                tracker.genie_room_name = room_details.get("genie_room_name", tracker.genie_room_name)
                if "conversation_id" in room_details:
                    tracker.conversation_id = room_details["conversation_id"]
            else:
                # Create new
                tracker = ConversationTracker(
                    thread_ts=thread_ts,
                    genie_room_id=room_details["genie_room_id"],
                    genie_room_name=room_details["genie_room_name"],
                    conversation_id=room_details.get("conversation_id")
                )
                session.add(tracker)
            
            session.commit()
        except SQLAlchemyError as e:
            print(f"Error setting conversation: {e}")
            session.rollback()
            raise
        finally:
            session.close()


def update_conversation_id(thread_ts: str, conversation_id: str):
    """
    Update the conversation_id for an existing thread.
    
    Args:
        thread_ts: Slack thread timestamp
        conversation_id: Genie conversation ID
    """
    if is_local_mode():
        if thread_ts in _local_conv_tracker:
            _local_conv_tracker[thread_ts]["conversation_id"] = conversation_id
    else:
        session = get_session()
        try:
            tracker = session.query(ConversationTracker).filter_by(thread_ts=thread_ts).first()
            if tracker:
                tracker.conversation_id = conversation_id
                session.commit()
        except SQLAlchemyError as e:
            print(f"Error updating conversation_id: {e}")
            session.rollback()
            raise
        finally:
            session.close()


def delete_conversation(thread_ts: str):
    """
    Delete conversation details for a thread.
    
    Args:
        thread_ts: Slack thread timestamp
    """
    if is_local_mode():
        if thread_ts in _local_conv_tracker:
            del _local_conv_tracker[thread_ts]
    else:
        session = get_session()
        try:
            tracker = session.query(ConversationTracker).filter_by(thread_ts=thread_ts).first()
            if tracker:
                session.delete(tracker)
                session.commit()
        except SQLAlchemyError as e:
            print(f"Error deleting conversation: {e}")
            session.rollback()
            raise
        finally:
            session.close()


def clear_all_conversations():
    """Clear all conversations. Use with caution!"""
    if is_local_mode():
        _local_conv_tracker.clear()
    else:
        session = get_session()
        try:
            session.query(ConversationTracker).delete()
            session.commit()
        except SQLAlchemyError as e:
            print(f"Error clearing conversations: {e}")
            session.rollback()
            raise
        finally:
            session.close()
