"""Chat endpoint for AI Todo Chatbot."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session
from datetime import datetime
from typing import Optional

from app.database import get_session
from app.auth import decode_access_token
from app.models.conversation import ChatRequest, ChatResponse
from app.services.conversation_service import ConversationService
from app.services.todo_service import TodoService
from app.mcp_server import MCPToolExecutor
from app.agent import TodoAgent
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

router = APIRouter(prefix="/api/chat", tags=["chat"])
security = HTTPBearer()


def get_current_user_id(credentials: HTTPAuthorizationCredentials = Depends(security)) -> int:
    """Extract and validate user ID from JWT token."""
    if not credentials:
        raise HTTPException(status_code=401, detail="Missing authentication credentials")
    token = credentials.credentials
    payload = decode_access_token(token)
    if not payload or "sub" not in payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return int(payload["sub"])


@router.post("/{user_id}", response_model=ChatResponse)
async def chat(
    user_id: int,
    request: ChatRequest,
    auth_user_id: int = Depends(get_current_user_id),
    session: Session = Depends(get_session)
):
    """
    Chat endpoint for AI-powered todo management.

    Process natural language messages and execute task operations via AI agent.
    """
    # Verify user owns this conversation
    if user_id != auth_user_id:
        raise HTTPException(status_code=403, detail="Unauthorized")

    # Validate request
    if not request.message or not request.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    try:
        print(f"[DEBUG] Chat started for user {user_id}")
        # Get or create conversation
        conversation = ConversationService.get_or_create_conversation(
            session, user_id, request.conversation_id
        )
        print(f"[DEBUG] Conversation: {conversation.id}")

        # Set conversation title from first message if needed
        if not conversation.title:
            title = request.message[:50]
            ConversationService.update_conversation_title(session, conversation.id, user_id, title)

        # Get recent messages for context
        recent_messages = ConversationService.get_recent_conversation_messages(
            session, conversation.id, user_id, limit=10
        )
        print(f"[DEBUG] Recent messages: {len(recent_messages)}")

        # Format conversation history for agent
        conversation_history = []
        for msg in recent_messages:
            conversation_history.append({
                "role": msg.role,
                "content": msg.content
            })

        # Get task summary for context
        task_summary = TodoService.get_user_statistics(session, user_id)
        print(f"[DEBUG] Task summary retrieved")

        # Initialize MCP executor
        mcp_executor = MCPToolExecutor(session, user_id)

        # Initialize and run agent
        print(f"[DEBUG] Initializing agent...")
        agent = TodoAgent(user_id, mcp_executor)
        agent.set_conversation_history(conversation_history)

        # Process message with agent
        print(f"[DEBUG] Calling agent.process_message...")
        agent_result = await agent.process_message(
            request.message,
            task_summary=task_summary
        )
        print(f"[DEBUG] Agent processing finished")

        # Store user message in database
        user_message = ConversationService.add_message(
            session,
            conversation.id,
            user_id,
            role="user",
            content=request.message
        )

        # Extract tool calls for storage
        tool_calls_data = [
            {
                "tool": tc["tool"],
                "parameters": tc["parameters"]
            }
            for tc in agent_result.get("tool_calls", [])
        ]

        tool_results_data = [
            {
                "tool": tc["tool"],
                "result": tc["result"]
            }
            for tc in agent_result.get("tool_calls", [])
        ]

        # Store assistant response in database
        print(f"[DEBUG] Storing assistant response...")
        assistant_message = ConversationService.add_message(
            session,
            conversation.id,
            user_id,
            role="assistant",
            content=agent_result.get("response", ""),
            tool_calls=tool_calls_data,
            tool_results=tool_results_data
        )

        # Return response with validated tool_calls
        tool_calls_list = agent_result.get("tool_calls", [])

        # Ensure tool_calls is a list of dicts only (no Union types)
        validated_tool_calls = []
        if isinstance(tool_calls_list, list):
            for tc in tool_calls_list:
                if isinstance(tc, dict):
                    validated_tool_calls.append(tc)

        print(f"[DEBUG] Sending response to client...")
        return ChatResponse(
            conversation_id=conversation.id,
            message_id=assistant_message.id,
            response=agent_result.get("response", ""),
            tool_calls=validated_tool_calls,
            timestamp=datetime.utcnow()
        )

    except HTTPException:
        raise
    except Exception as e:
        # Log error for debugging with full traceback
        import traceback
        error_trace = traceback.format_exc()
        print(f"Error in chat endpoint: {str(e)}")
        print(f"Error type: {type(e).__name__}")
        print(f"Full traceback:\n{error_trace}")
        raise HTTPException(
            status_code=500,
            detail=f"Backend Error [{type(e).__name__}]: {str(e)}"
        )


@router.get("/{user_id}/conversations")
async def get_conversations(
    user_id: int,
    skip: int = 0,
    limit: int = 50,
    auth_user_id: int = Depends(get_current_user_id),
    session: Session = Depends(get_session)
):
    """Get user's conversations."""
    if user_id != auth_user_id:
        raise HTTPException(status_code=403, detail="Unauthorized")

    try:
        conversations = ConversationService.get_user_conversations(
            session, user_id, skip=skip, limit=limit
        )
        return {
            "conversations": [
                {
                    "id": c.id,
                    "title": c.title,
                    "created_at": c.created_at,
                    "updated_at": c.updated_at,
                    "is_active": c.is_active
                }
                for c in conversations
            ],
            "total": len(conversations)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to retrieve conversations")


@router.get("/{user_id}/conversations/{conversation_id}/messages")
async def get_conversation_messages(
    user_id: int,
    conversation_id: int,
    skip: int = 0,
    limit: int = 100,
    auth_user_id: int = Depends(get_current_user_id),
    session: Session = Depends(get_session)
):
    """Get messages from a conversation."""
    if user_id != auth_user_id:
        raise HTTPException(status_code=403, detail="Unauthorized")

    try:
        # Verify conversation exists and belongs to user
        conversation = ConversationService.get_conversation(session, conversation_id, user_id)
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")

        messages = ConversationService.get_conversation_messages(
            session, conversation_id, user_id, skip=skip, limit=limit
        )

        return {
            "messages": [
                {
                    "id": m.id,
                    "role": m.role,
                    "content": m.content,
                    "tool_calls": m.get_tool_calls(),
                    "tool_results": m.get_tool_results(),
                    "created_at": m.created_at
                }
                for m in messages
            ],
            "total": len(messages)
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to retrieve messages")
