"""Database models for conversation tracking."""
from sqlalchemy import Column, String, DateTime, func
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

# Dedicated schema for the Genie Slack App
SCHEMA_NAME = "genie_app"


class ConversationTracker(Base):
    """
    Model for tracking Slack thread to Genie conversation mappings.
    
    Attributes:
        thread_ts: Slack thread timestamp (primary key)
        conversation_id: Genie conversation ID
        genie_room_id: Genie room/space ID
        genie_room_name: Genie room/space name
        created_at: Timestamp when the record was created
        updated_at: Timestamp when the record was last updated
    """
    __tablename__ = "conversation_tracker"
    __table_args__ = {'schema': SCHEMA_NAME}
    
    thread_ts = Column(String, primary_key=True)
    conversation_id = Column(String, nullable=True)
    genie_room_id = Column(String, nullable=False)
    genie_room_name = Column(String, nullable=False)
    created_at = Column(DateTime, server_default=func.current_timestamp())
    updated_at = Column(DateTime, server_default=func.current_timestamp(), onupdate=func.current_timestamp())
    
    def to_dict(self):
        """Convert model to dictionary format matching the old conv_tracker structure."""
        return {
            "conversation_id": self.conversation_id,
            "genie_room_id": self.genie_room_id,
            "genie_room_name": self.genie_room_name
        }


class MessageTracker(Base):
    """
    Model for tracking Slack message to Genie message mappings.
    Used for sending feedback (thumbs up/down) to Genie.
    
    Attributes:
        slack_message_ts: Slack message timestamp (primary key)
        slack_channel_id: Slack channel ID (primary key)
        space_id: Genie space/room ID
        conversation_id: Genie conversation ID
        message_id: Genie message ID
        created_at: Timestamp when the record was created
    """
    __tablename__ = "message_tracker"
    __table_args__ = {'schema': SCHEMA_NAME}
    
    slack_message_ts = Column(String, primary_key=True)
    slack_channel_id = Column(String, primary_key=True)
    space_id = Column(String, nullable=False)
    conversation_id = Column(String, nullable=False)
    message_id = Column(String, nullable=False)
    created_at = Column(DateTime, server_default=func.current_timestamp())
    
    def to_dict(self):
        """Convert model to dictionary format."""
        return {
            "space_id": self.space_id,
            "conversation_id": self.conversation_id,
            "message_id": self.message_id
        }
