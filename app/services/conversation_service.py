from sqlmodel import Session, select
from app.models.conversation import Conversation, Message, ConversationCreate, MessageCreate
from datetime import datetime
from typing import List, Optional


class ConversationService:
    """Service for managing conversations and messages."""

    @staticmethod
    def create_conversation(session: Session, user_id: int, title: Optional[str] = None) -> Conversation:
        """Create a new conversation."""
        conversation = Conversation(user_id=user_id, title=title, is_active=True)
        session.add(conversation)
        session.commit()
        session.refresh(conversation)
        return conversation

    @staticmethod
    def get_conversation(session: Session, conversation_id: int, user_id: int) -> Optional[Conversation]:
        """Get a specific conversation if it belongs to the user."""
        statement = select(Conversation).where(
            (Conversation.id == conversation_id) & (Conversation.user_id == user_id)
        )
        return session.exec(statement).first()

    @staticmethod
    def get_user_conversations(
        session: Session,
        user_id: int,
        skip: int = 0,
        limit: int = 50,
        active_only: bool = True
    ) -> List[Conversation]:
        """Get user's conversations."""
        statement = select(Conversation).where(Conversation.user_id == user_id)

        if active_only:
            statement = statement.where(Conversation.is_active == True)

        statement = statement.order_by(Conversation.updated_at.desc())
        return session.exec(statement.offset(skip).limit(limit)).all()

    @staticmethod
    def update_conversation_title(session: Session, conversation_id: int, user_id: int, title: str) -> Optional[Conversation]:
        """Update conversation title."""
        conversation = ConversationService.get_conversation(session, conversation_id, user_id)
        if not conversation:
            return None

        conversation.title = title
        conversation.updated_at = datetime.utcnow()
        session.add(conversation)
        session.commit()
        session.refresh(conversation)
        return conversation

    @staticmethod
    def close_conversation(session: Session, conversation_id: int, user_id: int) -> Optional[Conversation]:
        """Close (deactivate) a conversation."""
        conversation = ConversationService.get_conversation(session, conversation_id, user_id)
        if not conversation:
            return None

        conversation.is_active = False
        conversation.updated_at = datetime.utcnow()
        session.add(conversation)
        session.commit()
        session.refresh(conversation)
        return conversation

    @staticmethod
    def add_message(
        session: Session,
        conversation_id: int,
        user_id: int,
        role: str,
        content: str,
        tool_calls: Optional[List[dict]] = None,
        tool_results: Optional[List[dict]] = None
    ) -> Optional[Message]:
        """Add a message to a conversation."""
        # Verify conversation exists and belongs to user
        conversation = ConversationService.get_conversation(session, conversation_id, user_id)
        if not conversation:
            return None

        message = Message(
            conversation_id=conversation_id,
            user_id=user_id,
            role=role,
            content=content
        )
        if tool_calls:
            message.set_tool_calls(tool_calls)
        if tool_results:
            message.set_tool_results(tool_results)

        session.add(message)

        # Update conversation's updated_at timestamp
        conversation.updated_at = datetime.utcnow()
        session.add(conversation)

        session.commit()
        session.refresh(message)
        return message

    @staticmethod
    def get_conversation_messages(
        session: Session,
        conversation_id: int,
        user_id: int,
        skip: int = 0,
        limit: int = 100
    ) -> List[Message]:
        """Get messages from a conversation."""
        # Verify conversation belongs to user
        conversation = ConversationService.get_conversation(session, conversation_id, user_id)
        if not conversation:
            return []

        statement = select(Message).where(Message.conversation_id == conversation_id)
        statement = statement.order_by(Message.created_at.asc())
        return session.exec(statement.offset(skip).limit(limit)).all()

    @staticmethod
    def get_recent_conversation_messages(
        session: Session,
        conversation_id: int,
        user_id: int,
        limit: int = 10
    ) -> List[Message]:
        """Get recent messages from a conversation (for context)."""
        messages = ConversationService.get_conversation_messages(session, conversation_id, user_id)
        # Return last 'limit' messages
        return messages[-limit:] if len(messages) > limit else messages

    @staticmethod
    def delete_message(session: Session, message_id: int, user_id: int) -> bool:
        """Delete a message if it belongs to user."""
        statement = select(Message).where(
            (Message.id == message_id) & (Message.user_id == user_id)
        )
        message = session.exec(statement).first()

        if not message:
            return False

        session.delete(message)
        session.commit()
        return True

    @staticmethod
    def delete_conversation(session: Session, conversation_id: int, user_id: int) -> bool:
        """Delete a conversation and all its messages."""
        conversation = ConversationService.get_conversation(session, conversation_id, user_id)
        if not conversation:
            return False

        # Delete all messages in conversation
        statement = select(Message).where(Message.conversation_id == conversation_id)
        messages = session.exec(statement).all()
        for message in messages:
            session.delete(message)

        # Delete conversation
        session.delete(conversation)
        session.commit()
        return True

    @staticmethod
    def get_or_create_conversation(
        session: Session,
        user_id: int,
        conversation_id: Optional[int] = None
    ) -> Conversation:
        """Get existing conversation or create a new one."""
        if conversation_id:
            conversation = ConversationService.get_conversation(session, conversation_id, user_id)
            if conversation:
                return conversation

        # Create new conversation
        return ConversationService.create_conversation(session, user_id)
