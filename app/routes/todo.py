from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session
from app.database import get_session
from app.models.todo import TodoCreate, TodoUpdate, TodoRead
from app.services.todo_service import TodoService
from app.auth import decode_access_token
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

router = APIRouter(prefix="/api/todos", tags=["todos"])
security = HTTPBearer()


def get_current_user_id(credentials: HTTPAuthorizationCredentials = Depends(security)) -> int:
    if not credentials:
        raise HTTPException(status_code=401, detail="Missing authentication credentials")
    token = credentials.credentials
    payload = decode_access_token(token)
    if not payload or "sub" not in payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return int(payload["sub"])


@router.post("", response_model=TodoRead)
async def create_todo(
    todo_data: TodoCreate,
    user_id: int = Depends(get_current_user_id),
    session: Session = Depends(get_session)
):
    todo = TodoService.create_todo(session, user_id, todo_data)
    return todo


@router.get("", response_model=list[TodoRead])
async def get_todos(
    user_id: int = Depends(get_current_user_id),
    session: Session = Depends(get_session),
    search: str = None,
    priority: str = None,
    completed: bool = None,
    tag: str = None,
    sort_by: str = "created_at",
    sort_order: str = "desc",
    skip: int = 0,
    limit: int = 100
):
    todos = TodoService.get_user_todos(
        session,
        user_id,
        skip=skip,
        limit=limit,
        search=search,
        priority=priority,
        completed=completed,
        tag=tag,
        sort_by=sort_by,
        sort_order=sort_order
    )
    return todos


@router.get("/statistics")
async def get_statistics(
    user_id: int = Depends(get_current_user_id),
    session: Session = Depends(get_session)
):
    stats = TodoService.get_user_statistics(session, user_id)
    return stats


@router.get("/tags")
async def get_tags(
    user_id: int = Depends(get_current_user_id),
    session: Session = Depends(get_session)
):
    tags = TodoService.get_user_tags(session, user_id)
    return tags


@router.get("/{todo_id}", response_model=TodoRead)
async def get_todo(
    todo_id: int,
    user_id: int = Depends(get_current_user_id),
    session: Session = Depends(get_session)
):
    todo = TodoService.get_todo_by_id(session, todo_id, user_id)
    if not todo:
        raise HTTPException(status_code=404, detail="Todo not found")
    return todo


@router.put("/{todo_id}", response_model=TodoRead)
async def update_todo(
    todo_id: int,
    todo_update: TodoUpdate,
    user_id: int = Depends(get_current_user_id),
    session: Session = Depends(get_session)
):
    todo = TodoService.update_todo(session, todo_id, user_id, todo_update)
    if not todo:
        raise HTTPException(status_code=404, detail="Todo not found")
    return todo


@router.put("/{todo_id}/done", response_model=TodoRead)
async def mark_done(
    todo_id: int,
    user_id: int = Depends(get_current_user_id),
    session: Session = Depends(get_session)
):
    todo = TodoService.mark_done(session, todo_id, user_id)
    if not todo:
        raise HTTPException(status_code=404, detail="Todo not found")
    return todo


@router.put("/{todo_id}/undone", response_model=TodoRead)
async def mark_undone(
    todo_id: int,
    user_id: int = Depends(get_current_user_id),
    session: Session = Depends(get_session)
):
    todo = TodoService.mark_undone(session, todo_id, user_id)
    if not todo:
        raise HTTPException(status_code=404, detail="Todo not found")
    return todo


@router.delete("/{todo_id}")
async def delete_todo(
    todo_id: int,
    user_id: int = Depends(get_current_user_id),
    session: Session = Depends(get_session)
):
    success = TodoService.delete_todo(session, todo_id, user_id)
    if not success:
        raise HTTPException(status_code=404, detail="Todo not found")
    return {"message": "Todo deleted successfully"}
