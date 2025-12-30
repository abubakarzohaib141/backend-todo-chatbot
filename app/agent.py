import os
import json
import asyncio
from typing import Optional, List
from dotenv import load_dotenv
from app.config import settings
from agents import (
    Agent,
    Runner,
    function_tool,
    AsyncOpenAI,
    OpenAIChatCompletionsModel,
    set_tracing_disabled
)

# Disable tracing if not needed
set_tracing_disabled(disabled=True)

# API Configuration
GEMINI_API_KEY = settings.gemini_api_key

if not GEMINI_API_KEY:
    print("[WARNING] GEMINI_API_KEY is not set in settings!")
else:
    # Safe log of key presence
    print(f"[INFO] API Key loaded. Starts with: {GEMINI_API_KEY[:4]}...")

# 1. External Gemini client
external_client: AsyncOpenAI = AsyncOpenAI(
    api_key=GEMINI_API_KEY or "missing-key",
    base_url="https://openrouter.ai/api/v1",
)

# 2. Chat model for Gemini
llm_model: OpenAIChatCompletionsModel = OpenAIChatCompletionsModel(
    model="google/gemini-2.0-flash-001",
    openai_client=external_client
)


class TodoAgent:
    """AI Agent for managing todos via natural language using Gemini 2.5 Flash."""

    def __init__(self, user_id: int, mcp_executor):
        self.user_id = user_id
        self.mcp_executor = mcp_executor
        self.model = llm_model
        self.conversation_history: List[dict] = []

    def set_conversation_history(self, messages: List[dict]):
        self.conversation_history = messages

    async def process_message(self, user_message: str, task_summary: Optional[dict] = None) -> dict:
        """Process a user message and return AI response and tool calls."""

        # Build system prompt
        system_prompt = self._build_system_prompt(task_summary)

        # Prepare messages
        messages = self._prepare_messages(user_message)

        # Create tool functions that wrap the MCP executor
        async def add_task(title: str, description: str = "", priority: str = "medium", tags: str = "", due_date: str = "") -> str:
            """Add a new task.

            Args:
                title: The title of the task
                description: The description of the task
                priority: The priority level (low, medium, high)
                tags: Comma-separated tags
                due_date: Due date in ISO format

            Returns:
                JSON string with the created task details
            """
            print(f"[TOOL] add_task called with title: {title}")
            params = {
                "title": title,
                "description": description,
                "priority": priority,
                "tags": tags.split(",") if tags else [],
                "due_date": due_date if due_date else None
            }
            result = await self.mcp_executor.execute_tool("add_task", params)
            print(f"[TOOL] add_task result: {result}")
            return json.dumps(result)

        async def list_tasks(skip: int = 0, limit: int = 50, search: str = "", priority: str = "", completed: str = "") -> str:
            """List user's tasks with optional filtering.

            Args:
                skip: Number of tasks to skip
                limit: Maximum number of tasks to return
                search: Search query
                priority: Filter by priority
                completed: Filter by completion status (true/false)

            Returns:
                JSON string with list of tasks
            """
            params = {
                "skip": skip,
                "limit": limit,
                "search": search if search else None,
                "priority": priority if priority else None,
                "completed": completed.lower() == "true" if completed else None
            }
            result = await self.mcp_executor.execute_tool("list_tasks", params)
            return json.dumps(result)

        async def complete_task(task_id: int) -> str:
            """Mark a task as complete.

            Args:
                task_id: The ID of the task to mark as complete

            Returns:
                JSON string with the updated task
            """
            result = await self.mcp_executor.execute_tool("complete_task", {"task_id": task_id})
            return json.dumps(result)

        async def delete_task(task_id: int) -> str:
            """Delete a task.

            Args:
                task_id: The ID of the task to delete

            Returns:
                JSON string with confirmation
            """
            result = await self.mcp_executor.execute_tool("delete_task", {"task_id": task_id})
            return json.dumps(result)

        async def update_task(task_id: int, title: str = "", description: str = "", priority: str = "", completed: str = "") -> str:
            """Update a task.

            Args:
                task_id: The ID of the task to update
                title: New title (optional)
                description: New description (optional)
                priority: New priority level (optional)
                completed: New completion status (optional, true/false)

            Returns:
                JSON string with the updated task
            """
            params = {"task_id": task_id}
            if title:
                params["title"] = title
            if description:
                params["description"] = description
            if priority:
                params["priority"] = priority
            if completed:
                params["completed"] = completed.lower() == "true"
            result = await self.mcp_executor.execute_tool("update_task", params)
            return json.dumps(result)

        async def get_task(task_id: int) -> str:
            """Get a specific task.

            Args:
                task_id: The ID of the task to retrieve

            Returns:
                JSON string with task details
            """
            result = await self.mcp_executor.execute_tool("get_task", {"task_id": task_id})
            return json.dumps(result)

        # Create tools using function_tool decorator
        try:
            tools = [
                function_tool(add_task),
                function_tool(list_tasks),
                function_tool(complete_task),
                function_tool(delete_task),
                function_tool(update_task),
                function_tool(get_task),
            ]
            print(f"[DEBUG] Tools created successfully: {len(tools)} tools")
        except Exception as e:
            print(f"[ERROR] Failed to create tools: {e}")
            import traceback
            traceback.print_exc()
            raise

        # Create Agent with tools
        try:
            todo_agent = Agent(
                name="TodoAgent",
                instructions=system_prompt,
                model=self.model,
                tools=tools
            )
            print("[DEBUG] Agent created successfully")
        except Exception as e:
            print(f"[ERROR] Failed to create agent: {e}")
            import traceback
            traceback.print_exc()
            raise

        # Run agent
        try:
            print(f"[DEBUG] Running agent with message: {user_message[:50]}...")
            # Use only the user message as input, history is in instructions or managed by SDK
            # But the SDK usually takes history in provide_history or similar
            # Since the user's instructions mentioned history, we'll try to pass it in messages
            # If it fails, we'll try string input next
            result = await Runner.run(todo_agent, input=user_message)
            print(f"[DEBUG] Runner completed successfully")
        except Exception as e:
            print(f"[ERROR] Failed to run agent: {e}")
            print(f"[ERROR] Error type: {type(e).__name__}")
            import traceback
            traceback.print_exc()
            raise

        # Safely extract final_output
        final_output = ""
        try:
            if hasattr(result, "final_output"):
                final_output = str(result.final_output)
            elif isinstance(result, str):
                final_output = result
            else:
                # Some versions might return a different object
                final_output = str(result)
        except Exception as e:
            print(f"Error extracting final_output: {e}")

        # Safely extract tool_calls
        tool_calls = []
        try:
            # The SDK might have tool_calls on the result object
            raw_calls = getattr(result, "tool_calls", [])
            if not raw_calls and hasattr(result, "steps"):
                # Multi-step agents might have tool calls in steps
                for step in getattr(result, "steps", []):
                    if hasattr(step, "tool_calls"):
                        raw_calls.extend(step.tool_calls)

            for tc in raw_calls:
                call_data = {}
                if isinstance(tc, dict):
                    call_data = tc
                else:
                    # It's likely a ToolCall object or similar
                    call_data = {
                        "tool": getattr(tc, "name", getattr(tc, "tool_name", "unknown")),
                        "parameters": getattr(tc, "arguments", getattr(tc, "tool_arguments", {})),
                        "result": getattr(tc, "output", getattr(tc, "result", None))
                    }
                
                # Ensure parameters is a dict
                if isinstance(call_data.get("parameters"), str):
                    try:
                        call_data["parameters"] = json.loads(call_data["parameters"])
                    except:
                        pass
                
                tool_calls.append(call_data)
        except Exception as e:
            print(f"Error extracting tool_calls: {e}")

        return {
            "response": final_output,
            "tool_calls": tool_calls
        }

    def _build_system_prompt(self, task_summary: Optional[dict] = None) -> str:
        prompt = """You are a helpful AI assistant for managing tasks.
You have access to tools: add_task, list_tasks, complete_task, delete_task, update_task, get_task.
Respond friendly, confirm actions, ask for clarification if needed, include due dates if available."""

        # Add conversation history for context
        if self.conversation_history:
            prompt += "\n\nRecent conversation history:\n"
            for msg in self.conversation_history[-5:]: # Last 5 messages for conciseness
                role = "User" if msg["role"] == "user" else "Assistant"
                prompt += f"{role}: {msg['content']}\n"

        if task_summary:
            prompt += f"\n\nCurrent user task summary:\n"
            prompt += f"- Total tasks: {task_summary.get('total', 0)}\n"
            prompt += f"- Completed: {task_summary.get('completed', 0)}\n"
            prompt += f"- Pending: {task_summary.get('pending', 0)}\n"
            if task_summary.get('high_priority', 0):
                prompt += f"- High priority: {task_summary.get('high_priority', 0)}\n"
            if task_summary.get('due_today', 0):
                prompt += f"- Due today: {task_summary.get('due_today', 0)}\n"
            if task_summary.get('overdue', 0):
                prompt += f"- Overdue: {task_summary.get('overdue', 0)}\n"

        return prompt

    def _prepare_messages(self, user_message: str) -> List[dict]:
        # Include last 10 conversation messages
        messages = [{"role": msg["role"], "content": msg["content"]} for msg in self.conversation_history[-10:]]
        messages.append({"role": "user", "content": user_message})
        return messages


# Example usage
if __name__ == "__main__":
    async def main():
        todo_agent = TodoAgent(user_id=1, mcp_executor=None)
        result = await todo_agent.process_message("Add a task: Finish AI homework by tomorrow")
        print("\nAI RESPONSE:\n", result["response"])
        print("\nTOOL CALLS:\n", result["tool_calls"])

    asyncio.run(main())
