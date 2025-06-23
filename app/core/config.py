from typing import Any, Optional, List, Dict
from functools import lru_cache
from pydantic import BaseSettings, AnyHttpUrl, PostgresDsn
from typing import List, Optional

class Settings(BaseSettings):
    # === App Config ===
    PROJECT_NAME: str = "Pet Barbershop API"
    API_V1_STR: str = "/api/v1"
    DEBUG: bool = False

    # === CORS ===
    BACKEND_CORS_ORIGINS: List[AnyHttpUrl] = [
        "http://localhost",
        "http://localhost:3000",
        "https://gyvunukirpykla.me",
        "https://www.gyvunukirpykla.me",
        "https://api.gyvunukirpykla.me"
    ]

    # === Database ===
    DATABASE_URL: str = "sqlite:///./barbershop.db"
    # For PostgreSQL override via env:
    # DATABASE_URL: Optional[PostgresDsn] = None

    # === Security ===
    SECRET_KEY: str = "super-secret-key"  # ⚠️ Replace this for production!
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 1 day

    class Config:
        case_sensitive = True
        env_file = ".env"

@lru_cache()
def get_settings() -> Settings:
    return Settings()
