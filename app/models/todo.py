from sqlmodel import SQLModel, Field, Index
from typing import Optional, List
from datetime import datetime
from enum import Enum
import json


class PriorityLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class Todo(SQLModel, table=True):
    __tablename__ = "todos"
    __table_args__ = (
        Index("idx_user_id", "user_id"),
        Index("idx_user_completed", "user_id", "completed"),
        Index("idx_user_id_priority", "user_id", "priority"),
        Index("idx_user_id_created", "user_id", "created_at"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id")
    title: str
    description: Optional[str] = None
    completed: bool = False
    priority: str = "medium"
    tags_json: str = Field(default="[]")
    due_date: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    @property
    def tags(self) -> List[str]:
        """Deserialize tags from JSON string"""
        try:
            return json.loads(self.tags_json) if self.tags_json else []
        except:
            return []

    @tags.setter
    def tags(self, value: List[str]):
        """Serialize tags to JSON string"""
        self.tags_json = json.dumps(value) if value else "[]"


class TodoCreate(SQLModel):
    title: str
    description: Optional[str] = None
    completed: bool = False
    priority: str = "medium"
    tags: List[str] = Field(default_factory=list)
    due_date: Optional[datetime] = None


class TodoUpdate(SQLModel):
    title: Optional[str] = None
    description: Optional[str] = None
    completed: Optional[bool] = None
    priority: Optional[str] = None
    tags: Optional[List[str]] = None
    due_date: Optional[datetime] = None


class TodoRead(SQLModel):
    id: int
    user_id: int
    title: str
    description: Optional[str] = None
    completed: bool = False
    priority: str
    tags: List[str] = Field(default_factory=list)
    due_date: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
