"""
전역 설정 관리

환경 변수를 Pydantic BaseSettings로 관리합니다.
"""

from pydantic_settings import BaseSettings
from typing import Optional
import os #추가 26/02/10


class Settings(BaseSettings):
    """애플리케이션 설정"""
    
    # Application
    APP_ENV: str = "development"
    DEBUG: bool = True
    LOG_LEVEL: str = "INFO"
    
    # Database
    # DATABASE_URL: str
    DATABASE_URL: str = os.getenv("DATABASE_URL")
    DATABASE_HOST: str = "localhost"
    DATABASE_PORT: int = 5432
    DATABASE_USER: str = "memgarden"
    DATABASE_PASSWORD: str = "password"
    DATABASE_NAME: str = "memory_garden"

    REDIS_URL: str
    QDRANT_URL: str
    QDRANT_API_KEY: Optional[str] = None
    
    # AI Services
    CLAUDE_API_KEY: str
    ANTHROPIC_API_KEY: str
    OPENAI_API_KEY: str
    CLAUDE_MODEL: str = "claude-4-5-sonnet-20250929"
    GPT_MODEL: str = "gpt-4o-mini"
    
    # Kakao
    KAKAO_REST_API_KEY: Optional[str] = None
    KAKAO_ADMIN_KEY: Optional[str] = None
    KAKAO_CLIENT_SECRET: Optional[str] = None
    KAKAO_CHANNEL_ID: Optional[str] = None
    KAKAO_MOCK_MODE: bool = True  # False로 설정하면 실제 카카오톡 전송

    # Kakao OAuth (2026-02-12 추가)
    KAKAO_REDIRECT_URI: str = "https://n8n.softline.co.kr/api/v1/auth/kakao/callback"

    # 카카오 비즈메시지 (친구톡 채널→구독자 발송용)
    # 카카오 i 커넥트 메시지 서비스 가입 후 발급
    KAKAO_BIZ_CLIENT_ID: Optional[str] = None       # 비즈메시지 클라이언트 ID
    KAKAO_BIZ_CLIENT_SECRET: Optional[str] = None   # 비즈메시지 클라이언트 시크릿
    KAKAO_SENDER_KEY: Optional[str] = None           # 발신프로파일키 (40자)
    KAKAO_BIZ_BASE_URL: str = "https://bizmsg-web.kakaoenterprise.com"

    # Firebase Cloud Messaging (푸시 알림)
    FIREBASE_CREDENTIALS_PATH: str = "config/firebase-adminsdk.json"
    FIREBASE_PROJECT_ID: Optional[str] = None
    KAKAO_CHANNEL_DEEP_LINK: str = "kakaotalk://talk/chat/_ZeUTxl"

    # Firebase Web Push (Web App용)
    FIREBASE_API_KEY: Optional[str] = None
    FIREBASE_AUTH_DOMAIN: Optional[str] = None
    FIREBASE_MESSAGING_SENDER_ID: Optional[str] = None
    FIREBASE_APP_ID: Optional[str] = None
    FIREBASE_VAPID_KEY: Optional[str] = None
    
    # Security
    SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_HOURS: int = 24

    # CORS
    CORS_ORIGINS: str = "*"  # Comma-separated list for production
    
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"  # 기본값은 상황에 맞게 설정
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/0"

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
