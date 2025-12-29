from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional


class Settings(BaseSettings):
    app_name: str = "Todo App"
    debug: bool = False

    # Database
    database_url: str = "sqlite:///./todos.db"

    # JWT
    secret_key: str = Field(default="your-secret-key-change-this", alias="SECRET_KEY")
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    # CORS
    cors_origins: list = Field(
        default=[
            "http://localhost:3000",
            "http://localhost:3001",
            "http://localhost:8000",
            "http://localhost:8001",
            "http://127.0.0.1:3000",
            "http://127.0.0.1:3001",
            "http://127.0.0.1:8000",
            "http://127.0.0.1:8001",
            "https://hakthon-todo-app.vercel.app",
            "https://abubakaris-todo-app.hf.space",
        ],
        alias="CORS_ORIGINS"
    )

    # AI/LLM
    gemini_api_key: str = Field(default="", alias="GEMINI_API_KEY")

    class Config:
        env_file = ".env"
        case_sensitive = False
        populate_by_name = True


settings = Settings()
