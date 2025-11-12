# app/config.py
from pydantic_settings import BaseSettings
from typing import List

class Settings(BaseSettings):
    PROJECT_NAME: str = "UBTI Hiring Portal"
    
    DB_SERVER: str
    DB_PORT: int = 1433
    DB_NAME: str
    DB_USER: str
    DB_PASSWORD: str

    # ← CHANGE: Accept as string from .env
    BACKEND_CORS_ORIGINS: str = ""

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

    # ← Add method to get list
    def get_cors_origins(self) -> List[str]:
        if not self.BACKEND_CORS_ORIGINS:
            return []
        return [
            origin.strip()
            for origin in self.BACKEND_CORS_ORIGINS.split(",")
            if origin.strip()
        ]

settings = Settings()