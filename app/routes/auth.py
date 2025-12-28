from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session
from datetime import timedelta
from app.database import get_session
from app.models.user import UserCreate, UserRead
from app.services.user_service import UserService
from app.auth import create_access_token
from app.config import settings


router = APIRouter(prefix="/api/auth", tags=["auth"])


from pydantic import BaseModel


class LoginRequest(BaseModel):
    email: str
    password: str


@router.post("/register", response_model=UserRead)
async def register(user_data: UserCreate, session: Session = Depends(get_session)):
    existing_user = UserService.get_user_by_email(session, user_data.email)
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    user = UserService.create_user(session, user_data)
    return user


@router.post("/login")
async def login(request: LoginRequest, session: Session = Depends(get_session)):
    user = UserService.authenticate_user(session, request.email, request.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": str(user.id)},
        expires_delta=access_token_expires
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name
        }
    }


@router.post("/logout")
async def logout():
    return {"message": "Logged out successfully"}
