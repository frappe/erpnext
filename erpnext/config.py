import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from pydantic import BaseSettings

class Settings(BaseSettings):
    database_url: str = os.getenv("DATABASE_URL", "postgresql://user:password@localhost/Goldfish")
    secret_key: str = os.getenv("SECRET_KEY", "your-secret-key")
    app_name: str = "Goldfish"
    version: str = "1.0.0"
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")

settings = Settings()

engine = create_engine(settings.database_url)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()