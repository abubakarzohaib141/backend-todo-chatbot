"""MCP Server for task management operations."""
import json
from typing import Any
from sqlmodel import Session
from app.models.todo import TodoCreate, TodoUpdate
from app.services.todo_service import TodoService


class MCPToolExecutor:
    """Executes MCP tool calls within the application context."""

    def __init__(self, session: Session, user_id: int):
        self.session = session
        self.user_id = user_id

    async def execute_tool(self, tool_name: str, parameters: dict) -> dict:
        """Execute a tool call and return result."""
        print(f"[MCP] execute_tool called with tool_name: {tool_name}, parameters: {parameters}")
        if tool_name == "add_task":
            return self._add_task(parameters)
        elif tool_name == "list_tasks":
            return self._list_tasks(parameters)
        elif tool_name == "complete_task":
            return self._complete_task(parameters)
        elif tool_name == "delete_task":
            return self._delete_task(parameters)
        elif tool_name == "update_task":
            return self._update_task(parameters)
        elif tool_name == "get_task":
            return self._get_task(parameters)
        else:
            return {
                "success": False,
                "error": f"Unknown tool: {tool_name}",
                "message": f"Tool '{tool_name}' is not available"
            }

    def _add_task(self, params: dict) -> dict:
        """Add a new task."""
        try:
            print(f"[MCP] _add_task called with params: {params}")
            # Validate required fields
            if "title" not in params or not params["title"]:
                return {
                    "success": False,
                    "error": "Missing required field: title",
                    "message": "Task title is required"
                }

            # Validate priority if provided
            priority = params.get("priority", "medium")
            if priority not in ["low", "medium", "high"]:
                return {
                    "success": False,
                    "error": "Invalid priority level",
                    "message": "Priority must be 'low', 'medium', or 'high'"
                }

            # Create todo
            todo_data = TodoCreate(
                title=params.get("title"),
                description=params.get("description"),
                priority=priority,
                completed=False,
                tags=params.get("tags", []),
                due_date=params.get("due_date")
            )

            todo = TodoService.create_todo(self.session, self.user_id, todo_data)
            print(f"[MCP] Task created successfully: {todo.id}")

            result = {
                "success": True,
                "task_id": todo.id,
                "task": {
                    "id": todo.id,
                    "title": todo.title,
                    "description": todo.description,
                    "priority": todo.priority,
                    "completed": todo.completed,
                    "due_date": todo.due_date.isoformat() if todo.due_date else None,
                    "tags": todo.tags,
                    "created_at": todo.created_at.isoformat()
                },
                "message": "Task created successfully"
            }
            print(f"[MCP] Returning result: {result}")
            return result
        except Exception as e:
            print(f"[MCP] Exception in _add_task: {str(e)}")
            import traceback
            traceback.print_exc()
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to create task"
            }

    def _list_tasks(self, params: dict) -> dict:
        """List user's tasks with optional filtering."""
        try:
            todos = TodoService.get_user_todos(
                self.session,
                self.user_id,
                skip=params.get("skip", 0),
                limit=params.get("limit", 50),
                search=params.get("search"),
                priority=params.get("priority"),
                completed=params.get("completed"),
                tag=params.get("tag"),
                sort_by=params.get("sort_by", "created_at"),
                sort_order=params.get("sort_order", "desc")
            )

            return {
                "success": True,
                "tasks": [
                    {
                        "id": todo.id,
                        "title": todo.title,
                        "description": todo.description,
                        "priority": todo.priority,
                        "completed": todo.completed,
                        "due_date": todo.due_date.isoformat() if todo.due_date else None,
                        "tags": todo.tags,
                        "created_at": todo.created_at.isoformat(),
                        "updated_at": todo.updated_at.isoformat()
                    }
                    for todo in todos
                ],
                "total": len(todos),
                "skip": params.get("skip", 0),
                "limit": params.get("limit", 50),
                "message": "Tasks retrieved successfully"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to retrieve tasks"
            }

    def _complete_task(self, params: dict) -> dict:
        """Mark a task as complete."""
        try:
            if "task_id" not in params:
                return {
                    "success": False,
                    "error": "Missing required field: task_id",
                    "message": "Task ID is required"
                }

            task_id = params.get("task_id")
            todo = TodoService.mark_done(self.session, task_id, self.user_id)

            if not todo:
                return {
                    "success": False,
                    "error": "Task not found",
                    "message": "Could not find the specified task"
                }

            return {
                "success": True,
                "task_id": todo.id,
                "completed": todo.completed,
                "message": "Task marked as complete"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to complete task"
            }

    def _delete_task(self, params: dict) -> dict:
        """Delete a task."""
        try:
            if "task_id" not in params:
                return {
                    "success": False,
                    "error": "Missing required field: task_id",
                    "message": "Task ID is required"
                }

            task_id = params.get("task_id")
            success = TodoService.delete_todo(self.session, task_id, self.user_id)

            if not success:
                return {
                    "success": False,
                    "error": "Task not found",
                    "message": "Could not find the specified task"
                }

            return {
                "success": True,
                "task_id": task_id,
                "message": "Task deleted successfully"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to delete task"
            }

    def _update_task(self, params: dict) -> dict:
        """Update a task."""
        try:
            if "task_id" not in params:
                return {
                    "success": False,
                    "error": "Missing required field: task_id",
                    "message": "Task ID is required"
                }

            task_id = params.get("task_id")
            update_data = {k: v for k, v in params.items() if k != "task_id" and v is not None}

            if not update_data:
                return {
                    "success": False,
                    "error": "No fields to update",
                    "message": "At least one field must be updated"
                }

            # Create TodoUpdate with provided fields
            todo_update = TodoUpdate(**update_data)
            todo = TodoService.update_todo(self.session, task_id, self.user_id, todo_update)

            if not todo:
                return {
                    "success": False,
                    "error": "Task not found",
                    "message": "Could not find the specified task"
                }

            return {
                "success": True,
                "task_id": todo.id,
                "task": {
                    "id": todo.id,
                    "title": todo.title,
                    "description": todo.description,
                    "priority": todo.priority,
                    "completed": todo.completed,
                    "due_date": todo.due_date.isoformat() if todo.due_date else None,
                    "tags": todo.tags,
                    "created_at": todo.created_at.isoformat(),
                    "updated_at": todo.updated_at.isoformat()
                },
                "message": "Task updated successfully"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to update task"
            }

    def _get_task(self, params: dict) -> dict:
        """Get a specific task."""
        try:
            if "task_id" not in params:
                return {
                    "success": False,
                    "error": "Missing required field: task_id",
                    "message": "Task ID is required"
                }

            task_id = params.get("task_id")
            todo = TodoService.get_todo_by_id(self.session, task_id, self.user_id)

            if not todo:
                return {
                    "success": False,
                    "error": "Task not found",
                    "message": "Could not find the specified task"
                }

            return {
                "success": True,
                "task": {
                    "id": todo.id,
                    "title": todo.title,
                    "description": todo.description,
                    "priority": todo.priority,
                    "completed": todo.completed,
                    "due_date": todo.due_date.isoformat() if todo.due_date else None,
                    "tags": todo.tags,
                    "created_at": todo.created_at.isoformat(),
                    "updated_at": todo.updated_at.isoformat()
                },
                "message": "Task retrieved successfully"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to retrieve task"
            }
