"""
Configurações centrais da aplicação via variáveis de ambiente.
"""

from pydantic_settings import BaseSettings
from typing import List
import secrets


class Settings(BaseSettings):
    # App
    APP_NAME: str = "FINA"
    DEBUG: bool = False
    SECRET_KEY: str = secrets.token_urlsafe(32)

    # JWT
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24        # 24 horas
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    # Banco de dados PostgreSQL
    DATABASE_URL: str = "postgresql+asyncpg://fina_user:fina_pass@localhost:5432/fina_db"

    # Redis (cache e rate limiting)
    REDIS_URL: str = "redis://localhost:6379"

    # CORS
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:8080",
        "https://app.fina.com.br",
    ]

    # Anthropic (Claude IA)
    ANTHROPIC_API_KEY: str = ""
    AI_MODEL: str = "claude-sonnet-4-20250514"
    AI_MAX_TOKENS: int = 1024

    # Open Finance / Pluggy
    PLUGGY_CLIENT_ID: str = ""
    PLUGGY_CLIENT_SECRET: str = ""
    PLUGGY_BASE_URL: str = "https://api.pluggy.ai"

    # Criptografia de dados sensíveis
    ENCRYPTION_KEY: str = secrets.token_urlsafe(32)

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()