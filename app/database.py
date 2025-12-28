from sqlmodel import SQLModel, create_engine, Session
from app.config import settings
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get DATABASE_URL from environment
database_url = os.getenv("DATABASE_URL", settings.database_url)

# Create engine with appropriate configuration for Postgres
if "sqlite" in database_url:
    engine = create_engine(database_url, echo=True, connect_args={"check_same_thread": False})
else:
    # Postgres/Neon configuration with optimized pooling
    engine = create_engine(
        database_url,
        echo=True,
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20,
        pool_recycle=3600,  # Recycle connections after 1 hour
        connect_args={"connect_timeout": 10}
    )


def create_db_and_tables():
    SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        yield session


def init_db():
    """Initialize database - alias for create_db_and_tables"""
    create_db_and_tables()
