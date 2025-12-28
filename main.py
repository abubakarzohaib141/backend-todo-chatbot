from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.database import create_db_and_tables, init_db
from app.routes import auth, todo, chat
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Create app
app = FastAPI(
    title=settings.app_name,
    debug=settings.debug
)

# CORS middleware - MUST be added before routes
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    max_age=3600,
)

# Events
@app.on_event("startup")
def on_startup():
    create_db_and_tables()


# Routes
app.include_router(auth.router)
app.include_router(todo.router)
app.include_router(chat.router)


@app.get("/health")
async def health_check():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug
    )
