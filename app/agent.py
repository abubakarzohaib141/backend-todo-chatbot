import os
import json
import asyncio
from typing import Optional, List
from dotenv import load_dotenv
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

# Load environment variables
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    print("[WARNING] GEMINI_API_KEY is not set! Agent will likely fail.")

# 1. External Gemini client
external_client: AsyncOpenAI = AsyncOpenAI(
    api_key=GEMINI_API_KEY or "missing-key",
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
)

# 2. Chat model for Gemini
llm_model: OpenAIChatCompletionsModel = OpenAIChatCompletionsModel(
    model="gemini-2.0-flash",
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
            result: Runner = await Runner.run(todo_agent, input=messages)
            print(f"[DEBUG] Runner completed successfully")
        except Exception as e:
            print(f"[ERROR] Failed to run agent: {e}")
            print(f"[ERROR] Error type: {type(e).__name__}")
            import traceback
            traceback.print_exc()
            raise

        # Safely extract final_output
        final_output = ""
        if hasattr(result, "final_output") and result.final_output:
            output = result.final_output
            if isinstance(output, str):
                final_output = output
            else:
                # Handle non-string final_output by converting to string
                try:
                    final_output = str(output)
                except Exception as e:
                    print(f"Error converting final_output to string: {e}")
                    final_output = ""

        # Safely extract tool_calls, handling Union type issues
        tool_calls = []
        if hasattr(result, "tool_calls"):
            raw_tool_calls = getattr(result, "tool_calls", [])
            # Ensure tool_calls is a list and contains only serializable dicts
            if isinstance(raw_tool_calls, list):
                for tc in raw_tool_calls:
                    if isinstance(tc, dict):
                        tool_calls.append(tc)
                    else:
                        # Handle non-dict tool calls by converting to dict
                        try:
                            if hasattr(tc, "__dict__"):
                                tool_calls.append(tc.__dict__)
                            else:
                                print(f"Warning: Unable to serialize tool_call: {type(tc)}")
                        except Exception as e:
                            print(f"Error serializing tool_call: {e}")

        return {
            "response": final_output,
            "tool_calls": tool_calls
        }

    def _build_system_prompt(self, task_summary: Optional[dict] = None) -> str:
        prompt = """You are a helpful AI assistant for managing tasks.
You have access to tools: add_task, list_tasks, complete_task, delete_task, update_task, get_task.
Respond friendly, confirm actions, ask for clarification if needed, include due dates if available."""

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
