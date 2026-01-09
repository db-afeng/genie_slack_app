"""Conversation tracker operations - handles both in-memory and database storage."""
import os
from typing import Optional, Dict
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from database.connection import get_session, get_engine
from database.models import Base, ConversationTracker, MessageTracker, SCHEMA_NAME


# In-memory trackers for local development
_local_conv_tracker = {}
_local_message_tracker = {}  # Key: (channel_id, message_ts), Value: {space_id, conversation_id, message_id}


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


# ==================== Message Tracking Functions ====================
# These functions track the mapping between Slack messages and Genie messages
# to enable feedback (thumbs up/down) functionality.


def set_message(channel_id: str, message_ts: str, space_id: str, conversation_id: str, message_id: str):
    """
    Store a mapping between a Slack message and a Genie message.
    
    Args:
        channel_id: Slack channel ID
        message_ts: Slack message timestamp
        space_id: Genie space/room ID
        conversation_id: Genie conversation ID
        message_id: Genie message ID
    """
    if is_local_mode():
        _local_message_tracker[(channel_id, message_ts)] = {
            "space_id": space_id,
            "conversation_id": conversation_id,
            "message_id": message_id
        }
    else:
        session = get_session()
        try:
            tracker = MessageTracker(
                slack_channel_id=channel_id,
                slack_message_ts=message_ts,
                space_id=space_id,
                conversation_id=conversation_id,
                message_id=message_id
            )
            session.merge(tracker)  # Use merge to handle upsert
            session.commit()
        except SQLAlchemyError as e:
            print(f"Error setting message: {e}")
            session.rollback()
            raise
        finally:
            session.close()


def get_message(channel_id: str, message_ts: str) -> Optional[Dict]:
    """
    Get Genie message details for a Slack message.
    
    Args:
        channel_id: Slack channel ID
        message_ts: Slack message timestamp
        
    Returns:
        Dict with space_id, conversation_id, message_id or None if not found
    """
    if is_local_mode():
        return _local_message_tracker.get((channel_id, message_ts))
    else:
        session = get_session()
        try:
            tracker = session.query(MessageTracker).filter_by(
                slack_channel_id=channel_id,
                slack_message_ts=message_ts
            ).first()
            return tracker.to_dict() if tracker else None
        except SQLAlchemyError as e:
            print(f"Error getting message: {e}")
            return None
        finally:
            session.close()


def delete_message_tracking(channel_id: str, message_ts: str):
    """
    Delete tracking for a Slack message.
    
    Args:
        channel_id: Slack channel ID
        message_ts: Slack message timestamp
    """
    if is_local_mode():
        key = (channel_id, message_ts)
        if key in _local_message_tracker:
            del _local_message_tracker[key]
    else:
        session = get_session()
        try:
            tracker = session.query(MessageTracker).filter_by(
                slack_channel_id=channel_id,
                slack_message_ts=message_ts
            ).first()
            if tracker:
                session.delete(tracker)
                session.commit()
        except SQLAlchemyError as e:
            print(f"Error deleting message tracking: {e}")
            session.rollback()
            raise
        finally:
            session.close()
