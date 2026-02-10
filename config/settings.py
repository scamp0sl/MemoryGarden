"""
전역 설정 관리

환경 변수를 Pydantic BaseSettings로 관리합니다.
"""

from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """애플리케이션 설정"""
    
    # Application
    APP_ENV: str = "development"
    DEBUG: bool = True
    LOG_LEVEL: str = "INFO"
    
    # Database
    DATABASE_URL: str
    REDIS_URL: str
    QDRANT_URL: str
    QDRANT_API_KEY: Optional[str] = None
    
    # AI Services
    CLAUDE_API_KEY: str
    OPENAI_API_KEY: str
    CLAUDE_MODEL: str = "claude-4-5-sonnet-20250929"
    GPT_MODEL: str = "gpt-4o-2024-08-06"
    
    # Kakao
    KAKAO_REST_API_KEY: Optional[str] = None
    KAKAO_ADMIN_KEY: Optional[str] = None
    KAKAO_CHANNEL_ID: Optional[str] = None
    
    # Security
    SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_HOURS: int = 24
    
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"  # 기본값은 상황에 맞게 설정
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/0"

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
