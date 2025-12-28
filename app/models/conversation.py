from sqlmodel import SQLModel, Field, Index
from typing import Optional, List, Any
from datetime import datetime
import json


class Conversation(SQLModel, table=True):
    """Represents a chat conversation session for a user."""
    __tablename__ = "conversations"
    __table_args__ = (
        Index("idx_conversations_user_id", "user_id"),
        Index("idx_conversations_user_created", "user_id", "created_at"),
        Index("idx_conversations_user_active", "user_id", "is_active"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id")
    title: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    is_active: bool = True
    metadata_json: str = Field(default="{}")

    def get_metadata(self) -> dict:
        """Deserialize metadata from JSON string"""
        try:
            return json.loads(self.metadata_json) if self.metadata_json else {}
        except:
            return {}

    def set_metadata(self, value: dict):
        """Serialize metadata to JSON string"""
        self.metadata_json = json.dumps(value) if value else "{}"


class ConversationCreate(SQLModel):
    title: Optional[str] = None
    is_active: bool = True


class ConversationUpdate(SQLModel):
    title: Optional[str] = None
    is_active: Optional[bool] = None


class ConversationRead(SQLModel):
    id: int
    user_id: int
    title: Optional[str]
    created_at: datetime
    updated_at: datetime
    is_active: bool

    class Config:
        from_attributes = True


class Message(SQLModel, table=True):
    """Represents a single message in a conversation."""
    __tablename__ = "messages"
    __table_args__ = (
        Index("idx_messages_conversation_id", "conversation_id"),
        Index("idx_messages_user_id", "user_id"),
        Index("idx_messages_created_at", "created_at"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    conversation_id: int = Field(foreign_key="conversations.id")
    user_id: int = Field(foreign_key="users.id")
    role: str  # "user" or "assistant"
    content: str
    tool_calls_json: str = Field(default="[]")
    tool_results_json: str = Field(default="[]")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    metadata_json: str = Field(default="{}")

    def get_tool_calls(self) -> List[dict]:
        """Deserialize tool calls from JSON string"""
        try:
            return json.loads(self.tool_calls_json) if self.tool_calls_json else []
        except:
            return []

    def set_tool_calls(self, value: List[dict]):
        """Serialize tool calls to JSON string"""
        self.tool_calls_json = json.dumps(value) if value else "[]"

    def get_tool_results(self) -> List[dict]:
        """Deserialize tool results from JSON string"""
        try:
            return json.loads(self.tool_results_json) if self.tool_results_json else []
        except:
            return []

    def set_tool_results(self, value: List[dict]):
        """Serialize tool results to JSON string"""
        self.tool_results_json = json.dumps(value) if value else "[]"

    def get_metadata(self) -> dict:
        """Deserialize metadata from JSON string"""
        try:
            return json.loads(self.metadata_json) if self.metadata_json else {}
        except:
            return {}

    def set_metadata(self, value: dict):
        """Serialize metadata to JSON string"""
        self.metadata_json = json.dumps(value) if value else "{}"


class MessageCreate(SQLModel):
    conversation_id: int
    role: str
    content: str
    tool_calls: Optional[List[dict]] = None
    tool_results: Optional[List[dict]] = None


class MessageUpdate(SQLModel):
    content: Optional[str] = None
    tool_calls: Optional[List[dict]] = None
    tool_results: Optional[List[dict]] = None


class MessageRead(SQLModel):
    id: int
    conversation_id: int
    user_id: int
    role: str
    content: str
    tool_calls_json: str = Field(default="[]")
    tool_results_json: str = Field(default="[]")
    created_at: datetime
    metadata_json: str = Field(default="{}")

    class Config:
        from_attributes = True


class ChatRequest(SQLModel):
    """Request body for chat endpoint"""
    message: str
    conversation_id: Optional[int] = None


class ChatResponse(SQLModel):
    """Response from chat endpoint"""
    conversation_id: int
    message_id: int
    response: str
    tool_calls: List[Any] = Field(default_factory=list)
    timestamp: datetime

    class Config:
        # Allow arbitrary types and be lenient with tool_calls
        arbitrary_types_allowed = True
