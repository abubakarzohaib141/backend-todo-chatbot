from sqlmodel import Session, select
from app.models.user import User, UserCreate
from app.auth import get_password_hash, verify_password


class UserService:
    @staticmethod
    def create_user(session: Session, user_data: UserCreate) -> User:
        hashed_password = get_password_hash(user_data.password)
        user = User(
            email=user_data.email,
            full_name=user_data.full_name,
            hashed_password=hashed_password
        )
        session.add(user)
        session.commit()
        session.refresh(user)
        return user

    @staticmethod
    def get_user_by_email(session: Session, email: str) -> User:
        statement = select(User).where(User.email == email)
        return session.exec(statement).first()

    @staticmethod
    def get_user_by_id(session: Session, user_id: int) -> User:
        return session.get(User, user_id)

    @staticmethod
    def authenticate_user(session: Session, email: str, password: str) -> User:
        user = UserService.get_user_by_email(session, email)
        if not user or not verify_password(password, user.hashed_password):
            return None
        return user
