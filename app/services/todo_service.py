from sqlmodel import Session, select, or_, update
from app.models.todo import Todo, TodoCreate, TodoUpdate, PriorityLevel
from typing import Optional, List
from datetime import datetime, timedelta
import json


class TodoService:
    @staticmethod
    def create_todo(session: Session, user_id: int, todo_data: TodoCreate) -> Todo:
        todo_dict = todo_data.dict()
        tags = todo_dict.pop('tags', [])
        todo = Todo(**todo_dict, user_id=user_id)
        todo.tags = tags
        session.add(todo)
        session.commit()
        session.refresh(todo)
        return todo

    @staticmethod
    def get_user_todos(
        session: Session,
        user_id: int,
        skip: int = 0,
        limit: int = 100,
        search: Optional[str] = None,
        priority: Optional[str] = None,
        completed: Optional[bool] = None,
        tag: Optional[str] = None,
        sort_by: str = "created_at",
        sort_order: str = "desc"
    ) -> list[Todo]:
        statement = select(Todo).where(Todo.user_id == user_id)

        # Search filter (by title or description)
        if search:
            statement = statement.where(
                or_(
                    Todo.title.ilike(f"%{search}%"),
                    Todo.description.ilike(f"%{search}%")
                )
            )

        # Priority filter
        if priority:
            statement = statement.where(Todo.priority == priority)

        # Completed filter
        if completed is not None:
            statement = statement.where(Todo.completed == completed)

        # Tag filter
        if tag:
            # Simple tag filtering (checks if tag is in the list)
            todos = session.exec(statement).all()
            todos = [t for t in todos if tag.lower() in [tag_item.lower() for tag_item in t.tags]]
            return todos

        # Sorting
        if sort_by == "priority":
            # Custom priority ordering: HIGH > MEDIUM > LOW
            priority_order = {"high": 0, "medium": 1, "low": 2}
            todos = session.exec(statement).all()
            todos.sort(
                key=lambda x: priority_order.get(x.priority, 3),
                reverse=(sort_order == "desc")
            )
            return todos[skip : skip + limit]
        elif sort_by == "due_date":
            statement = statement.order_by(
                Todo.due_date.asc() if sort_order == "asc" else Todo.due_date.desc()
            )
        elif sort_by == "title":
            statement = statement.order_by(
                Todo.title.asc() if sort_order == "asc" else Todo.title.desc()
            )
        else:  # created_at (default)
            statement = statement.order_by(
                Todo.created_at.asc() if sort_order == "asc" else Todo.created_at.desc()
            )

        return session.exec(statement.offset(skip).limit(limit)).all()

    @staticmethod
    def get_todo_by_id(session: Session, todo_id: int, user_id: int) -> Todo:
        statement = select(Todo).where((Todo.id == todo_id) & (Todo.user_id == user_id))
        return session.exec(statement).first()

    @staticmethod
    def update_todo(session: Session, todo_id: int, user_id: int, todo_update: TodoUpdate) -> Todo:
        todo = TodoService.get_todo_by_id(session, todo_id, user_id)
        if not todo:
            return None

        update_data = todo_update.dict(exclude_unset=True)
        for key, value in update_data.items():
            setattr(todo, key, value)

        session.add(todo)
        session.commit()
        session.refresh(todo)
        return todo

    @staticmethod
    def delete_todo(session: Session, todo_id: int, user_id: int) -> bool:
        todo = TodoService.get_todo_by_id(session, todo_id, user_id)
        if not todo:
            return False

        session.delete(todo)
        session.commit()
        return True

    @staticmethod
    def mark_done(session: Session, todo_id: int, user_id: int) -> Todo:
        # Direct update for better performance
        statement = update(Todo).where(
            (Todo.id == todo_id) & (Todo.user_id == user_id)
        ).values(completed=True, updated_at=datetime.utcnow())
        session.exec(statement)
        session.commit()
        # Fetch updated todo
        return TodoService.get_todo_by_id(session, todo_id, user_id)

    @staticmethod
    def mark_undone(session: Session, todo_id: int, user_id: int) -> Todo:
        # Direct update for better performance
        statement = update(Todo).where(
            (Todo.id == todo_id) & (Todo.user_id == user_id)
        ).values(completed=False, updated_at=datetime.utcnow())
        session.exec(statement)
        session.commit()
        # Fetch updated todo
        return TodoService.get_todo_by_id(session, todo_id, user_id)

    @staticmethod
    def get_user_statistics(session: Session, user_id: int) -> dict:
        """Get statistics for user's todos"""
        todos = session.exec(select(Todo).where(Todo.user_id == user_id)).all()

        completed_count = sum(1 for t in todos if t.completed)
        pending_count = len(todos) - completed_count
        high_priority_count = sum(1 for t in todos if t.priority == "high" and not t.completed)

        # Calculate overdue count
        now = datetime.utcnow()
        overdue_count = sum(1 for t in todos if t.due_date and t.due_date < now and not t.completed)

        # Calculate due today count
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = today_start + timedelta(days=1)
        due_today_count = sum(1 for t in todos if t.due_date and today_start <= t.due_date < today_end and not t.completed)

        # Calculate due this week count
        week_end = now + timedelta(days=7)
        due_this_week_count = sum(1 for t in todos if t.due_date and now <= t.due_date <= week_end and not t.completed)

        total_count = len(todos)
        completion_percentage = int((completed_count / total_count * 100)) if total_count > 0 else 0

        return {
            "total": total_count,
            "completed": completed_count,
            "pending": pending_count,
            "completion_percentage": completion_percentage,
            "high_priority": high_priority_count,
            "overdue": overdue_count,
            "due_today": due_today_count,
            "due_this_week": due_this_week_count,
        }

    @staticmethod
    def get_user_tags(session: Session, user_id: int) -> List[dict]:
        """Get all unique tags for user with usage counts"""
        todos = session.exec(select(Todo).where(Todo.user_id == user_id)).all()

        tag_counts = {}
        for todo in todos:
            for tag in todo.tags:
                tag_lower = tag.lower()
                tag_counts[tag_lower] = tag_counts.get(tag_lower, 0) + 1

        return [{"name": tag, "count": count} for tag, count in sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)]
