"""Database models for conversation tracking."""
from sqlalchemy import Column, String, DateTime, func
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


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
