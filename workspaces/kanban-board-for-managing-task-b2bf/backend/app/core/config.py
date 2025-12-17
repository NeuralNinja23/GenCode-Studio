from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import List

class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    """
    # Project Info
    PROJECT_NAME: str = "GenCode App"
    VERSION: str = "0.1.0"
    API_V1_STR: str = "/api"
    
    # CORS
    BACKEND_CORS_ORIGINS: List[str] = ["http://localhost:5173", "http://localhost:5174", "http://localhost:3000"]

    # Database (MongoDB)
    MONGO_URL: str = "mongodb://localhost:27017"
    DB_NAME: str = "app_db"
    
    # Security (Defaults provided for dev, MUST be overridden in prod)
    SECRET_KEY: str = "development_secret_key_change_me"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days

    class Config:
        case_sensitive = True
        env_file = ".env"

@lru_cache()
def get_settings():
    return Settings()

settings = get_settings()
